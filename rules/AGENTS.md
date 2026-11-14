# Harness Rules and Directives

Always-on rules for `agy` sessions, subteams, and swarms.

## 1. Functional Coder & Rich Hickey Directives

Follow functional programming paradigms inspired by Rich Hickey:
- Information is plain data: prefer maps, sets, and vectors over class
  hierarchies and bespoke object encapsulation.
- Pure functions: separate pure computation from stateful side-effects.
- Polymorphism via data: favor multimethods and protocols over class
  inheritance.
- Schema à la carte: specify schemas flexibly where needed (e.g., Malli or
  Clojure Spec) without rigid compile-time class coupling.
- Idiom: 100 functions operating on 1 data structure are better than 10
  functions operating on 10 data structures.
- Semantic naming: make data keys and function names convey exact domain
  intent.
- Skill trigger: activate the `functional-coder` skill whenever designing,
  refactoring, or implementing functional code architectures.

## 2. Property-Based Testing (PBT) Mandate

Every non-trivial transformation or data pipeline requires property-based
testing to ensure robustness across generated inputs:
- Unit tests verify specific known examples; PBT verifies fundamental
  invariants, algebraic properties, and round-trip consistency.
- Python ecosystem: require `hypothesis` for generating test strategies,
  fuzzing inputs, and shrinking failing cases.
- Clojure ecosystem: require `malli.generator` and `clojure.test.check` to
  validate schemas and generator-backed invariants.
- Coverage requirement: unit tests alone are insufficient for core business
  logic, schema validations, serializers, or data transformations.

## 3. Asynchronous Swarm & Teamwork Model

Multi-agent coordination inside swarms must avoid synchronous lockstep and
idle waiting:
- Subteam Couple: each feature stream is owned by a paired subteam composed
  of an Executioner (`gemini-3.8-flash-medium`) and a Reviewer/Auditor
  (`gemini-4-hydrogen-medium`).
- Conflict-Free Git Topology:
  - Each subteam member operates in its own isolated working copy
    (`workspace: "share"`).
  - Dedicated branches: Executioner works on `subteam/<id>/work`; Reviewer
    audits and verifies on `subteam/<id>/review`.
  - Non-blocking pipeline: Executioner continuously commits increments to
    `subteam/<id>/work` and notifies Reviewer without pausing. Reviewer
    pulls and audits committed SHAs asynchronously.
- Targeted Message Board Etiquette:
  - Structured message tags:
    - `[READY <sha>]`: Executioner signals a new commit ready for audit.
    - `[PASS <sha>]`: Reviewer confirms verification passes for that SHA.
    - `[FIX <sha>]`: Reviewer reports required fixes with file and line.
    - `[BLOCK <sha>]`: Reviewer signals critical blocking defect.
    - `[done]`: Final completion signal when all increments pass.
  - Targeted `@mentions`: wake only the specific peer working the handoff.
    Never use `@all` for status updates or routine audits.
  - Compact referencing: cite board message sequence numbers (`#<seq>`)
    instead of quoting message histories.
- Ultimate Review Gate:
  - Prior to merging to trunk or finishing high-stakes deliveries, final
    verification must run through a heterogeneous multi-model panel.
  - Swarm panel: employ Pro models from diverse model families (e.g.,
    Gemini 4 Hydrogen, Claude Opus 5.5, and GPT-OSS 120B) to audit logic,
    security, and architectural soundness from contrasting perspectives.

## 4. Graphics and UI Wireframes

Whenever graphics, terminal displays, dashboards, or UI designs are
illustrated:
- Require explicit ASCII-art wireframes to visualize screen layouts,
  element hierarchies, and component placements.
- Ensure all ASCII diagrams conform strictly to the 80-character line width
  boundary.
- Use structured box-drawing characters or standard ASCII symbols (`+`, `-`,
  `|`, `[ ]`, `( )`) for clarity and deterministic rendering across terminals.
