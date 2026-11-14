# Polya's Four Steps for Software Engineering

> "If you can't solve a problem, then there is an easier problem you can solve:
> find it."
> — George Polya, *How to Solve It* (1945)

George Polya's four-phase framework was written for mathematics, yet it maps
directly to software architecture, root-cause debugging, and algorithmic
design. Skipping early phases guarantees wasted typing; skipping Phase 4
guarantees repeating the same bugs.

```
+---------------+     +--------------+     +---------------+     +-----------+
| 1. Understand | --> | 2. Devise    | --> | 3. Carry Out  | --> | 4. Look   |
|    Problem    |     |    a Plan    |     |    the Plan   |     |    Back   |
+---------------+     +--------------+     +---------------+     +-----------+
        ^                     ^                    |                   |
        |   contradiction     |   stall / failed   |                   |
        +---------------------+--- assumption -----+                   |
        |                                                              |
        +-------------- generalize primitive / regression guard -------+
```

---

## Phase 1: Understand the Problem

Before proposing a fix or writing a function, separate the *problem space*
(what must be true) from the *solution space* (how to implement it).

### Diagnostic Questions

* **What is the unknown?**
  In design: what exact output, state transition, or invariant must hold?
  In debugging: what observable symptom diverges from specification?
* **What are the data?**
  What inputs, schemas, logs, and environment constraints are actually given?
* **What is the condition?**
  What invariants, latency budgets, concurrency rules, or boundary schemas
  must be satisfied simultaneously?
* **Is it possible to satisfy the condition?**
  Check for contradictory requirements before writing code. Are two constraints
  mutually exclusive (e.g., zero latency + synchronous global consensus)?
* **Draw a figure and introduce suitable notation.**
  Sketch an ASCII data-flow diagram or state machine. Replace vague prose
  ("the stuff gets processed") with precise qualified names (`:order/status`).

### Practical Moves

1. **Problem Restatement & Input-Output Contract**
   Strip framework jargon and express the task as an explicit contract before
   touching code:

   ```
   +---------------+--------------------------------------------------------+
   | Contract Slot | Concrete Specification                                 |
   +---------------+--------------------------------------------------------+
   | Inputs (Data) | Exact types, ranges, nullability, arrival rate         |
   | Output (Goal) | Return value, side effects, emitted events/errors      |
   | Preconditions | What callers guarantee (auth, sortedness, schema)      |
   | Invariants    | Properties true before & after (balance conservation)  |
   | Failure Modes | Expected behavior on timeout, duplicate, invalid input |
   +---------------+--------------------------------------------------------+
   ```

2. **Explicit Constraints & Non-Goals**
   Write three short lists:
   * *Hard bounds*: non-negotiable limits (backward compatibility, memory cap).
   * *Soft preferences*: nice-to-have trade-offs (ergonomics, future hooks).
   * *Non-goals*: problems explicitly out of scope right now. Naming non-goals
     prevents gold-plating and false dilemmas.
3. **Concrete Grounding Cases**
   Instantiate the problem with two tiny examples before generalizing: one
   minimal happy path (`n = 2`) and one sharp edge case (empty, duplicate, or
   partial failure).

---

## Phase 2: Devise a Plan

Connect the given data to the unknown. A plan is a verifiable strategy with
clear falsification criteria, not a guess.

### Planning Questions

* **Have you seen a related problem before?**
  Recognize structural isomorphism (e.g., dependency resolution is a DAG
  topological sort; rate limiting is a token bucket).
* **Look at the unknown.**
  Find a familiar problem with the same or a similar unknown.
* **Could you restate the problem?**
  Translate between domains (loops -> set operations; flags -> state machine)
  until the bottleneck becomes obvious.
* **Did you use all the data and the whole condition?**
  If your proposed architecture ignores a stated concurrency constraint or
  backwards-compatibility requirement, the plan is defective.

### Practical Moves

1. **Compare at Least Two Candidate Plans**
   Avoid anchoring on the first idea. Sketch two distinct options (e.g., simple
   in-memory scan vs. indexed store; local patch vs. schema fix) and evaluate
   them with explicit decision criteria:

   ```
   +-------------------+---------------------------------------------------+
   | Criterion         | Favor Plans That...                               |
   +-------------------+---------------------------------------------------+
   | Reversibility     | Can be rolled back cleanly via config or revert   |
   | Blast Radius      | Isolate change behind a narrow module boundary    |
   | Verification Cost | Allow fast, deterministic REPL or unit testing    |
   | Assumption Count  | Require fewest unproven runtime/infra assumptions |
   | Time-to-Signal    | Falsify the riskiest hypothesis earliest          |
   +-------------------+---------------------------------------------------+
   ```

2. **Risk-First Milestone Ordering**
   Sequence steps so the *hardest or riskiest unknown* is tested first via a
   thin vertical slice, instead of building boilerplate around unproven logic.
3. **Pre-Flight Sanity Check**
   Verify back-of-the-envelope bounds before coding: data volume (`O(n)` vs
   `O(n^2)`), idempotence on retry, failure recovery, and migration safety.

---

## Phase 3: Carry Out the Plan

Execution requires discipline, small verifiable increments, and willingness to
abort a broken plan early.

### Execution Rules

* **Check each step.**
  Can you see clearly that each transformation is correct? Prove or test each
  step in isolation (e.g., via REPL evaluation or a targeted property).
* **Keep steps small and reversible.**
  Never refactor three subsystems simultaneously. Verify each pure helper
  before composing them.
* **If the plan stalls, return to Phase 2.**
  Do not brute-force a failing hypothesis by piling on special-case patches.

### Practical Moves

1. **Incremental Checkpointing**
   Work in 15-30 minute verifiable increments. After each step passes its
   local check, checkpoint the known-good state (commit locally or save a green
   test) so a failed experiment reverts cleanly in seconds.
2. **Intermediate Invariant Guards**
   Validate preconditions and postconditions at step boundaries (assertions,
   schema checks, intermediate counts) rather than waiting for an end-to-end
   run to fail mysteriously.
3. **Explicit Stall & Pivot Triggers**
   Stop coding and return to Phase 2 (or Phase 1) immediately when:
   * You need a third ad-hoc `if` branch to patch around edge cases.
   * Two consecutive fixes fix one test while breaking an adjacent one.
   * A Phase 1 assumption about data shape or system behavior proves false.

---

## Phase 4: Look Back

Most engineers stop the moment tests turn green. Polya insists that the
highest leverage lives in post-solution reflection.

### Reflection Questions

* **Examine the solution.**
  Can you verify the result using an independent method?
* **Can you derive the result differently?**
  Is there a simpler, un-complected formulation with fewer moving parts?
* **Can you use the result or method for another problem?**
  Extract reusable pure primitives or generalizable invariants for the wider
  system, without premature over-abstraction.

### Practical Moves

1. **Independent Oracle & Stress Verification**
   Do not rely solely on tests written from the same mental model as the code:
   * Cross-check fast algorithms against a slow, obvious brute-force oracle on
     small randomized inputs (property-based testing).
   * Run inverse round-trip checks (`decode(encode(x)) == x`) and boundary
     probes (`0`, `1`, empty, max size, duplicates).
2. **Simplification & Deletion Pass**
   Re-read the complete diff with fresh eyes. Delete dead flags, unused
   abstractions, and speculative hooks added while exploring.
3. **Post-Fix Generalization & Class-of-Bugs Audit**
   Ask: *"Where else in this codebase does this violated assumption occur?"*
   Audit sibling endpoints, parsers, or workers for the same bug class. Extract
   a shared pure helper only once two or more concrete callers need it.
4. **Regression Guard & Knowledge Capture**
   Convert the triggering scenario into a permanent regression test or runtime
   invariant guard. Record *why* the constraint exists (and what false leads
   were eliminated) to counter hindsight bias in future incidents.
