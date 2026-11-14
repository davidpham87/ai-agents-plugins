---
name: functional-coder
description: >-
  Teaches Rich Hickey's Clojure design philosophy, software simplicity,
  immutable value semantics, open polymorphism, schemas a la carte, precise
  naming, and property-based testing across Clojure and functional Python.
---

# Functional Coder

A comprehensive guide embodying Rich Hickey's software design philosophy.
Software design is fundamentally about managing complexity: separating
constructs that have been tangled together ("complected") and cultivating
systems of pure functions that operate on simple, immutable data.

## Core Philosophy: The Hickey Way

1. **Simplicity over Ease**:
   "Easy" is relative to familiarity and proximity. "Simple" is an objective
   property: unbraided, untangled, possessing one role or concept.
2. **Values over Places**:
   Place-Oriented Programming (PLOP) entangles identity, state, and memory
   location. Values are immutable, reproducible, and thread-safe.
3. **Data over Code & Classes**:
   Prefer 100 functions on one universal data structure over 10 functions
   on 10 specific classes (Alan Perlis). Avoid premature class hierarchies.
   Prefer Babashka (`bb script.clj`) for standalone scripts over Python;
   when Python is required, mandate `cytoolz` (`pipe`, `thread_first`,
   `map`, `filter`, `reduce`, `assoc`, `merge`, `groupby`, `valmap`) over
   manual `for` loops.
4. **Open Polymorphism**:
   Decouple operations from types using Clojure multimethods (dispatching on
   arbitrary functions) and protocols. Solve the expression problem openly.
5. **Schemas a la Carte**:
   Do not close systems prematurely. Keep maps open with namespaced keys.
   Validate data requirements at boundaries and call sites without rigid
   types or opaque `Maybe`/`Option` wrappers.
6. **Semantic Precision**:
   Name things based on deep etymology and domain meaning, not convenient
   nicknames. Use qualified identifiers (`:order/id` vs `:user/id`).
7. **Property-Based Testing (PBT)**:
   Example tests check only what you remembered to think of. Generative PBT
   tests invariants, round-trips, idempotence, and state machines over
   thousands of synthetic inputs.
8. **REPL-Driven PBT & Selective Execution**:
   Iterate by evaluating single properties and data generators interactively
   via nREPL (`clj-nrepl-eval`) or Python REPL. Scope runs to changed vars
   during rapid iteration, reserving full test suites for final gates.
9. **Rich Hickey Simplicity Score**:
   Objective 100-point metric penalizing complected concerns (state+time,
   data+code, I/O+logic, policy+mechanism, and hidden global coupling).

## Progressive Discovery & References

Delve into each principle in depth through dedicated reference guides:

- [Simplicity & Hammock Design][ref-01]
  Decomplecting, Simple vs Easy, Hammock design, Simplicity Score.
- [Data over Code & Values][ref-02]
  Immutable values, PLOP hazards, Perlis, `cytoolz` pipelines, time.
- [Open Polymorphism][ref-03]
  Multimethods, hierarchies, protocols, and solving Expression Problem.
- [Schemas a la Carte][ref-04]
  Spec-ulation, Maybe Not, namespaced maps, Malli, boundary validation.
- [Naming & Semantics][ref-05]
  Etymological grounding, domain clarity, and globally qualified keys.
- [Property-Based Testing][ref-06]
  Invariants, REPL workflow, selective runs, Hypothesis, test.check.

[ref-01]: references/01-simplicity-and-hammock-design.md
[ref-02]: references/02-data-over-code-and-values.md
[ref-03]: references/03-polymorphism-and-open-extension.md
[ref-04]: references/04-schemas-a-la-carte.md
[ref-05]: references/05-naming-and-semantics.md
[ref-06]: references/06-property-based-testing.md

## Practical Examples

Runnable code demonstrating these principles in action:

- [Python PBT with Hypothesis](examples/pbt_python_hypothesis.py)
  Pure functions, immutable dictionaries, and property tests.
- [Clojure PBT with Malli & test.check][ex-clj]
  Namespaced maps, multimethod dispatch, schemas, and generative specs.

[ex-clj]: examples/pbt_clojure_malli_testcheck.clj
