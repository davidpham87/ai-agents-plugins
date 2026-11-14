# Async Coordination, State, Reducers, and Transducers

Clojure handles concurrency, state, and data pipelines by decomplecting
*what* a computation does from *when*, *where*, and *how* values move.

```
Pure Domain Logic (xforms, state transitions)
        |
        +---> Data Pipelines: Transducers (single-thread, zero-alloc)
        |                     Reducers r/fold (CPU-bound fork/join)
        |
        +---> Async Flow:     core.async channels + go / thread
        |
        +---> Shared State:   atom (synchronous CAS snapshots)
```

---

## 1. Managing State with Atoms

An `atom` holds a synchronous, uncoordinated **identity** pointing to
an immutable **value** over time.

### Core Rules for `atom`
* **Reads are lock-free**: `@state` (or `(deref state)`) returns an
  immutable snapshot immediately without blocking writers.
* **Updates must be pure**: `(swap! state f args...)` uses hardware
  compare-and-swap (CAS). Under contention, `f` may run **multiple
  times** before succeeding. Never put I/O, logging, or channel puts
  inside `swap!`.
* **React after commit with `swap-vals!`**: Capture `[old new]`
  atomically, then perform side effects outside the CAS loop.

```clojure
(defonce !sessions (atom {} :validator map?))

(defn upsert-session
  [sessions {:session/keys [id] :as session}]
  (assoc sessions id session))

(defn save-session!
  [session]
  (let [[prev curr] (swap-vals! !sessions upsert-session session)]
    {:prev-count (count prev)
     :curr-count (count curr)}))
```

### Observers and Validation
* **`:validator`**: A pure predicate checked before every commit; throws
  if an invalid value is proposed, keeping the atom uncorrupted.
* **`add-watch`**: Registers `(fn [k ref old-val new-val] ...)` to react
  to committed transitions. Keep watchers fast or push events to a
  `core.async` channel instead of blocking inside the watch.

### `atom` vs. `core.async` State Loops
* Use an **`atom`** when multiple callers need instant, lock-free reads
  of the current snapshot and transitions are pure functions.
* Use a **`core.async` loop** when state changes must serialize async
  I/O steps or enforce strict backpressure on incoming commands.

---

## 2. Async Coordination with `core.async`

`clojure.core.async` implements Communicating Sequential Processes
(CSP). Producers and consumers never call each other directly; they
communicate by putting values onto and taking values from **channels**.

```
Producer ---> [ chan (buffer + optional xform) ] ---> Consumer
  (>! / >!!)                                          (<! / <!!)
```

### `go` Blocks vs. `thread`
* **`go` (`<!`, `>!`, `alts!`)**: Rewrites code into a lightweight state
  machine parked on a fixed, small thread pool (typically `2 * cores`).
  Use `go` for coordination and fast in-memory work. **Never run
  blocking I/O** (HTTP, JDBC, `Thread/sleep`, `<!!`) inside a `go`
  block—doing so starves the entire dispatch pool.
* **`thread` (`<!!`, `>!!`)**: Allocates a dedicated OS thread from a
  cached pool. Use `thread` (or `pipeline-blocking`) for blocking I/O.

```clojure
(require '[clojure.core.async :as a :refer [<! >! go thread chan]])

(defn fetch-async
  [fetch-fn req]
  (thread (fetch-fn req)))

(defn coordinate!
  [in-ch out-ch timeout-ms]
  (go
    (loop []
      (when-let [msg (<! in-ch)]
        (let [t (a/timeout timeout-ms)
              [res port] (a/alts! [(fetch-async identity msg) t])]
          (>! out-ch (if (= port t) {:error :timeout} res))
          (recur))))))
```

### Backpressure and Buffers
* **Unbuffered `(chan)`**: Rendezvous; writer parks until reader takes.
* **Fixed `(chan n)`**: Applies backpressure once `n` items are queued.
* **`(dropping-buffer n)`**: Drops *new* puts when full (sheds load).
* **`(sliding-buffer n)`**: Drops *oldest* items when full (keeps
  freshest telemetry/UI ticks).
* **Always `close!` finite channels**: `<!` returns `nil` on closed,
  drained channels (`nil` cannot be put onto a channel).
* **Fan-out / Parallelism**: Use `pub`/`sub` or `mult`/`tap` for
  broadcasting, and `pipeline` / `pipeline-blocking` / `pipeline-async`
  for bounded parallel worker stages without manual `go` plumbing.

---

## 3. Transducers: Context-Independent Pipelines

A **transducer** (`xform`) is a composable transformation recipe that
decomplects *what* happens to elements from *what collection, stream, or
channel* carries them.

```clojure
(def order-xf
  (comp
    (filter :order/paid?)
    (map :order/total-cents)))
```

Because `order-xf` builds zero intermediate lazy sequences, the **exact
same** transducer runs everywhere:

```clojure
;; 1. Eager collection build
(into [] order-xf orders)

;; 2. Direct single-pass reduction
(transduce order-xf + 0 orders)

;; 3. Lazy sequence view or re-usable eduction
(sequence order-xf orders)
(eduction order-xf orders)

;; 4. Inside a core.async channel (processes items as they arrive)
(let [ex-handler (fn [err] {:error (.getMessage err)})
      ch         (chan 32 order-xf ex-handler)]
  ch)
```

### Practical Notes on Transducers
* **Composition order**: `(comp f g)` applies `f` *first*, then `g`
  (left-to-right data flow, unlike ordinary function composition).
* **Stateful transducers**: `dedupe`, `distinct`, `take`, and
  `partition-all` allocate internal `volatile!` state per reduction or
  channel instance—do not share an already-instantiated reducing fn
  across threads.
* **Channel error handling**: Always pass an `ex-handler` to `(chan n
  xf ex-handler)` in production so exceptions inside `xf` do not
  silently kill channel processing.

---

## 4. Reducers (`clojure.core.reducers`)

While transducers optimize single-stream pipelines across diverse
contexts, **`clojure.core.reducers`** optimizes **parallel, CPU-bound
fold reductions** over large in-memory collections (vectors and maps).

* **How `r/fold` works**: Splits an underlying tree-backed vector or map
  via Fork/Join into chunks (default 512), reduces each chunk with
  `reducef`, and merges partial results with `combinef`.
* **Monoid requirement**: `combinef` must be associative and return an
  identity value when called with **zero arguments** `(combinef)`.

```clojure
(require '[clojure.core.reducers :as r])

(defn sum-paid-totals
  [orders]
  (->> orders
       (r/filter :order/paid?)
       (r/map :order/total-cents)
       (r/fold +)))
```

> **Note**: Reducers skip intermediate collections, too, but `r/fold`
> falls back to sequential reduction on lazy seqs (`range`, lists). Use
> vectors or maps when seeking parallel speedup.

---

## 5. Choosing the Right Mechanism

```
Mechanism           Best For                        Parallel?
------------------  ------------------------------  ------------------
Lazy Seq (->>)      Small/infinite pull pipelines   No (chunked lazy)
Transducer (xf)     Zero-alloc reusable recipes,    No (unless via
                    into, transduce, core.async     async/pipeline)
Reducer (r/fold)    CPU-bound fold on big vectors   Yes (Fork/Join)
core.async/pipeline Bounded parallel I/O or CPU     Yes (worker pool)
                    stages with backpressure
atom (swap!)        Fast lock-free shared state     CAS retries
```

### Architectural Summary
1. Write domain logic as **pure functions** and **transducers**.
2. Keep mutable state in **`atom`**s (for synchronous snapshots) or
   isolated **`core.async`** state loops (for ordered async commands).
3. Put blocking I/O on **`thread`** or **`pipeline-blocking`**, never
   inside `go` blocks or `swap!`.
4. Reach for **`r/fold`** when profiling shows CPU-bound reduction over
   large vectors or maps.
