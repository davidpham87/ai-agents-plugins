# Polya's Heuristics Toolbox

When a direct path from inputs to solution is blocked, Polya recommends
systematic transformations of the problem itself. Below are eight core
heuristics adapted for software engineering.

---

## 1. Working Backwards

Start from the desired end state and trace what must immediately precede it.
* **Architecture**: Define the exact output schema or API response first,
  then work backwards to the pure transformations and boundary inputs needed
  to produce it.
* **Debugging**: Start at the failing assertion or corrupted state and trace
  upstream data flow until you reach the first divergence from expectation.

## 2. Auxiliary Problem

If you cannot solve the original problem, invent a simpler or related
**auxiliary problem** whose solution unlocks the real one.
* Build a minimal pure in-memory prototype (skipping I/O, auth, and HTTP) to
  validate the core algorithm in the REPL before wiring side effects.
* Drop one constraint temporarily (e.g., single-threaded before distributed)
  to isolate the essential structure.

## 3. Generalization and the Inventor's Paradox

**The Inventor's Paradox**: Sometimes the more general problem is *easier* to
solve than the specific one because extraneous special cases disappear.
* Instead of writing five brittle `if/elif` handlers for five message types,
  generalize to a data-driven dispatch table or multimethod.
* Instead of proving a property for one hardcoded list, state the general
  invariant over all valid inputs and test it with Hypothesis or `test.check`.

## 4. Specialization

Move in the opposite direction when a general problem feels overwhelming:
examine concrete, minimal boundary cases.
* Test with empty collections `[]`, single-element maps, `0`, or minimal
  shrunk counterexamples from a property-based test.
* If a general invariant fails on `n = 1`, it cannot hold for `n = 1000`.

## 5. Analogy

Map an unfamiliar domain onto a well-understood structural twin.
* Rate limiting -> token bucket or leaky bucket.
* Build pipelines -> directed acyclic graph (DAG) evaluation.
* Event sourcing -> append-only immutable log with left-fold projection.
* Verify that the analogy holds on edge cases; discard it where it leaks.

## 6. Decomposing and Recombining

Break a complex problem into independent sub-problems, solve each cleanly,
and recombine the pieces.
* Separate pure computation from I/O (functional core, imperative shell).
* Separate policy (what rule applies) from mechanism (how data moves).
* Ensure sub-problems are disjoint so solving one does not break another.

## 7. Invariants

Identify what *must not change* across transformations, retries, or state
transitions.
* Conservation laws (e.g., total ledger balance before and after transfer).
* Ordering or cardinality preservation (e.g., sorting keeps multiset equal).
* Idempotence (`f(f(x)) = f(x)`) for safe retries in distributed systems.

## 8. Restating the Problem

Translate the problem into a different representation where the answer becomes
obvious.
* Convert nested imperative loops into relational joins or set operations.
* Convert an English bug report into a minimal failing unit/property test.
* Convert implicit state flags into an explicit state-transition diagram.
