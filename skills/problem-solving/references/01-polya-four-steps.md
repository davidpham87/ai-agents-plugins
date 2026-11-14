# Polya's Four Steps for Software Engineering

> "If you can't solve a problem, then there is an easier problem you can solve:
> find it."
> — George Polya, *How to Solve It* (1945)

George Polya's four-phase framework was written for mathematics, yet it maps
directly to software architecture, root-cause debugging, and algorithmic
design. Skipping early phases guarantees wasted typing.

---

## Phase 1: Understand the Problem

Before proposing a fix or writing a function, answer Polya's diagnostic
questions:

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
  mutually exclusive?
* **Draw a figure and introduce suitable notation.**
  Sketch an ASCII data-flow diagram or state machine. Replace vague prose
  ("the stuff gets processed") with precise qualified names (`:order/status`).

---

## Phase 2: Devise a Plan

Connect the given data to the unknown. A plan is a clear, verifiable strategy,
not a guess.

* **Have you seen a related problem before?**
  Recognize structural isomorphism (e.g., dependency resolution is a DAG
  topological sort; rate limiting is a token bucket).
* **Look at the unknown.**
  Find a familiar problem with the same or a similar unknown.
* **Could you restate the problem?**
  Strip away framework jargon and express the core relationship in plain
  domain terms.
* **Did you use all the data and the whole condition?**
  If your proposed architecture ignores a stated concurrency constraint or
  backwards-compatibility requirement, the plan is defective.

---

## Phase 3: Carry Out the Plan

Execution requires discipline and continuous verification:

* **Check each step.**
  Can you see clearly that each transformation is correct? Can you prove or
  test it in isolation (e.g., via REPL evaluation or a targeted property)?
* **Keep steps small and reversible.**
  Never refactor three subsystems simultaneously. Verify each pure helper
  before composing them.
* **If the plan stalls, return to Phase 2.**
  Do not brute-force a failing hypothesis by piling on special-case patches.

---

## Phase 4: Look Back

Most engineers stop the moment tests turn green. Polya insists that the
highest leverage lives in reflection:

* **Examine the solution.**
  Can you check the result using an independent method (e.g., a property-based
  test oracle or inverse round-trip check)?
* **Can you derive the result differently?**
  Is there a simpler, un-complected formulation with fewer moving parts?
* **Can you use the result or method for another problem?**
  Extract reusable pure primitives or generalizable invariants for the wider
  system, without premature over-abstraction.
