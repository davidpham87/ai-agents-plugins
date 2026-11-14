# Data over Code and Value Semantics

> "It is better to have 100 functions operate on one data structure than 10
> functions on 10 data structures."
> — Alan J. Perlis, Epigrams on Programming (1982)

Rich Hickey's keynote *The Value of Values* (2012) challenges the foundational
assumption of mainstream imperative and object-oriented programming: that
computation should center on mutable memory locations.

---

## 1. The Value of Values

A **value** is an immutable piece of information.
* Numbers (`42`, `3.14159`)
* Dates (`2026-11-14`)
* Strings (`"clojure"`)
* Pure collections: vectors, maps, and sets containing values

Values cannot be altered. You cannot change the number `42` into `43`; you can
only compute a new value (`(+ 42 1)`).

In contrast, **Place-Oriented Programming (PLOP)** builds systems around
mutable containers: memory slots, variables, pointers, and object fields.
PLOP destroys history:
* **Spooky Action at a Distance**: Two subroutines sharing a pointer can
  mutate it behind each other's backs.
* **Concurrency Collapse**: Reading a mutable place requires locking, mutexes,
  or defensive copying to avoid torn reads.
* **Loss of Reproducibility**: When a bug occurs, you cannot inspect the
  exact value that caused it, because subsequent operations overwrote the
  memory.

Values are intrinsically thread-safe, freely shareable, cacheable, and
trivially testable.

---

## 2. Plain Data Structures over Custom Classes

Object-oriented programming encourages wrapping every conceptual entity in a
bespoke class with proprietary getters, setters, and private fields.

Consider the consequences of creating a `CustomerRecord` class vs. using an
associative map:

```clojure
;; Plain data: open, transparent, universally accessible
{:customer/id   "cust-8491"
 :customer/name "Ada Lovelace"
 :customer/tier :premium}
```

When data is represented in generic associative maps, sets, and vectors:
* Every standard library function (`map`, `filter`, `reduce`, `assoc`,
  `dissoc`, `get-in`, `update`) works immediately without adapters.
* Serialization to JSON, EDN, Transit, or SQL requires zero boilerplate mapping
  layers or DTO definitions.
* You do not need an abstract factory visitor proxy to access a field.

Alan Perlis's epigram captures this truth: by standardizing on a tiny handful of
general-purpose collection abstractions, you maximize functional leverage.

---

## 3. Separating Identity, State, and Time

In imperative systems, "identity" and "value" are complected into a single
construct: the memory address of an object. Hickey decomplects these into three
orthogonal concepts:

```
                      TIME  ==========================>
Identity: "Account"    o --------------> o -------------> o
Value (State):     [$100.00]         [$125.00]         [$75.00]
                      ^                 ^                 ^
                      Snapshot t0       Snapshot t1       Snapshot t2
```

1. **Value**: An unchanging magnitude, quantity, or immutable record.
2. **State**: The value associated with an identity at a specific point in time.
3. **Identity**: A logical named entity that references different immutable
   values over time (e.g., "my bank balance", "the current user session").
4. **Time**: The sequence or causal ordering of state transitions.

### The Epochal Time Model

Clojure implements the **Epochal Time Model** via reference types:
* `clojure.lang.Atom`: Synchronous, uncoordinated atomic updates via CAS
  (compare-and-swap).
* `clojure.lang.Ref`: Coordinated synchronous updates via Software
  Transactional Memory (STM).
* `clojure.lang.Agent`: Asynchronous autonomous updates via thread pools.

In all cases, reading a reference type (`@my-atom` or `(deref my-atom)`)
yields an immutable value snapshot in constant time with **zero locks**.
Readers never block writers, and writers never block readers.


---

## 4. Prefer Babashka (`bb`) and Python `cytoolz` Pipelines

For standalone automation and CLI scripts, **prefer Babashka (`bb script.clj`)**
over Python. Babashka gives instant startup, native Clojure immutable maps
and vectors, threading macros (`->>`, `->`), and built-in `babashka.fs` /
`babashka.process` without JVM boot lag.

When Python is required (e.g., for `ast` inspection or `hypothesis`),
imperative `for` loops with mutating accumulators (`res = []`, `d[k] = v`)
reintroduce Place-Oriented Programming (PLOP). Mandate `cytoolz` for
Clojure-style data transformations:

* **Threading**: `pipe` (`->>` / `->` via `curried`) and `thread_first`.
* **Sequence transforms**: `cytoolz.curried.map`, `filter`, `reduce`,
  `groupby`, `pluck`.
* **Immutable dict transforms**: `assoc`, `dissoc`, `merge`, `update_in`,
  `valmap`, `keymap` (all return new dicts without mutating inputs).

```python
from cytoolz import pipe, merge, assoc, valmap
from cytoolz.curried import map as cmap, filter as cfilter, groupby

# Clojure (->> items (filter active?) (map price) (reduce + 0))
total = pipe(
    items,
    cfilter(lambda it: it.get("item/qty", 0) > 0),
    cmap(lambda it: it["item/price"] * it["item/qty"]),
    sum,
)
```

Prefer declarative `cytoolz` pipelines over manual `for` loops whenever
transforming collections or associative maps.
