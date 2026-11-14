# Polya's Heuristics Toolbox

When a direct path from inputs to solution is blocked, Polya recommends
systematic transformations of the problem itself. Each heuristic below pairs
**when to use**, **how to apply**, and a concrete **example**.

```
+-----------------------------------+------------------------------------+
| Where You Are Stuck               | Reach For                          |
+-----------------------------------+------------------------------------+
| Too many paths forward            | 1. Working Backwards               |
| Tangled constraints / I/O         | 2. Wishful Thinking & Relaxation   |
| No bridge from data to goal       | 3. Auxiliary Elements / Scaffold   |
| Too abstract OR too many branches | 4. Abstraction Ladder              |
| Slow / clunky loops or flags      | 5. Representation Shift            |
| Mirror cases / subtle state bugs  | 6. Symmetry & Invariants           |
| Unsure if plan holds at edges     | 7. Extreme & Boundary Cases        |
| Rules mixed with I/O & plumbing   | 8. Decomposing & Recombining       |
| Unfamiliar domain jargon          | 9. Analogy & Isomorphism           |
| Hard to solve for size N at once  | 10. Incremental Construction       |
+-----------------------------------+------------------------------------+
```

---

## 1. Working Backwards

* **When to use**: The target output or failure state is clear, but forward
  search branches too widely.
* **How to apply**: Fix the exact desired end state. Ask what must immediately
  precede it, and trace upstream step by step until you reach known inputs.
* **Example**: In API design, define the exact response schema first, then
  derive the pure transforms and DB queries needed to populate it. In
  debugging, start at a corrupted ledger row and trace upstream mutations to
  the first divergent event.

## 2. Wishful Thinking & Constraint Relaxation

* **When to use**: A problem feels impossible because one hard constraint
  (concurrency, persistence, scale, or auth) tangles the core logic.
* **How to apply**: Pretend a magic helper `solve_part()` already exists, or
  temporarily drop the hardest constraint (solve single-threaded, in-memory,
  or without retries). Solve the relaxed core cleanly, then implement the
  helper or re-introduce constraints one at a time.
* **Example**: Prototype a billing reconciliation algorithm as a pure
  in-memory function in the REPL first; once verified, add database locks and
  an idempotent outbox around it.

## 3. Auxiliary Elements & Scaffolding

* **When to use**: Given inputs and the target output lack a direct link—like
  a geometry proof that needs an extra construction line.
* **How to apply**: Introduce an intermediate artifact that reveals hidden
  structure: a sentinel node, reverse index, prefix-sum array, monotonic
  stack, correlation ID, or adapter layer. Delete temporary scaffolding once
  it has served its purpose.
* **Example**: Prepend a dummy `head` sentinel node to eliminate empty-list
  edge cases in linked-list deletion, or inject a `correlation_id` across
  async queues so distributed traces join cleanly.

## 4. Abstraction Ladder: Specialize <-> Generalize

```
   GENERALIZE (Climb Up)   ^   Drops brittle special cases (Inventor's Paradox)
   ------------------------+---------------------------------------------------
   SPECIALIZE (Climb Down) v   Reveals mechanics on tiny concrete examples
```

* **When to use**: Climb *down* when an abstract specification feels opaque.
  Climb *up* when special cases explode into nested `if/elif` branches
  (**Polya's Inventor's Paradox**: the general problem can be easier than the
  specific one).
* **How to apply**:
  * *Specialize*: Fix `n = 1` or `n = 2` with concrete values to watch the
    mechanics work by hand.
  * *Generalize*: Replace enumerated cases with a data-driven rule, dispatch
    table, or universal invariant over all valid inputs.
* **Example**: Trace a job scheduler by hand for 2 jobs on 1 worker before
  coding for `N` workers (climb down). Replace five bespoke webhook handlers
  with one schema-driven dispatch map (climb up).

## 5. Representation Shift (Data-Structure & Model Re-framing)

* **When to use**: Operations feel slow (`O(n^2)`), fragile, or buried under
  nested conditionals in the current data model.
* **How to apply**: Convert the problem to an equivalent representation where
  the core operation becomes `O(1)` or obvious: nested loops -> sets/joins,
  boolean flags -> finite-state machine, mutable snapshots -> append-only
  event log, intervals -> sorted sweep-line endpoints.
* **Example**: Replace four interacting booleans (`is_paid`, `is_shipped`,
  `is_cancelled`, `is_refunded`) with an explicit state-transition table so
  illegal combinations become unrepresentable.

## 6. Symmetry & Invariants

* **When to use**: Mirror-image inputs duplicate logic, or state transforms
  across loops, retries, and concurrent workers risk subtle drift.
* **How to apply**:
  * *Symmetry*: Canonicalize inputs (e.g., sort pairs) so mirror cases share
    one code path.
  * *Invariants*: Name quantities that *must not change* (conservation laws,
    multiset preservation, monotonicity, idempotence `f(f(x)) = f(x)`) and
    assert them across transitions.
* **Example**: Store undirected graph edges as `(min(u, v), max(u, v))` to
  halve edge-lookup logic. Enforce `sum(debits) == sum(credits)` as a runtime
  invariant on every ledger commit.

## 7. Extreme & Boundary Cases

* **When to use**: Stress-testing a proposed plan before writing full code, or
  hunting subtle off-by-one and empty-collection bugs.
* **How to apply**: Push every dimension to its limits: `0`, `1`, empty `[]`,
  `null`, max capacity, all-equal values, already-sorted/reverse-sorted
  inputs, cycles, or simultaneous bursts.
* **Example**: Check cursor pagination when `items = []`, `page_size = 1`,
  and when all records share an identical timestamp. If the invariant fails
  at `n = 1`, it cannot hold at `n = 1000`.

## 8. Decomposing and Recombining

* **When to use**: Business rules, I/O, retries, and formatting are tangled
  together, making isolated verification impossible.
* **How to apply**: Split along natural seams into disjoint sub-problems with
  narrow interfaces: functional core vs. imperative shell, or policy (what
  rule applies) vs. mechanism (how data moves). Verify each part before
  recombining.
* **Example**: Extract pure tax and discount computation from HTTP handlers
  and SQL queries so pricing rules can be property-tested in milliseconds.

## 9. Analogy & Structural Isomorphism

* **When to use**: Domain vocabulary feels unfamiliar or hides a well-studied
  algorithmic structure.
* **How to apply**: Strip domain nouns and map the relationship onto a known
  twin: rate limiting -> token bucket, build order -> DAG topological sort,
  calendar conflicts -> interval merging. Explicitly verify where the analogy
  leaks on edge cases.
* **Example**: Treat service startup dependencies as a DAG topological sort,
  then verify the edge case where a cycle must emit a clear diagnostic error
  rather than looping forever.

## 10. Incremental Construction (Base Case -> Step)

* **When to use**: Solving for size `n` in one leap feels overwhelming in
  algorithms, streaming state, or multi-step migrations.
* **How to apply**: Solve trivially for `n = 0` or `n = 1`. Then ask:
  *"Given a valid solution for `n - 1`, what minimal delta produces `n`?"*
  Express the solution as `init` plus a pure `step(state, item)` transition.
* **Example**: Build a streaming window aggregator by defining the empty
  accumulator and one `step(acc, event)` update, or run a zero-downtime
  schema migration as small, reversible expand-and-contract steps.
