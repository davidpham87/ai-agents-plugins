# Harness Rules and Directives

Always-on rules for `agy` sessions, subteams, and swarms.

## 1. Functional Coder & Rich Hickey Directives

Follow functional programming paradigms inspired by Rich Hickey:
- Information is plain data: prefer maps, sets, and vectors over class
  hierarchies and bespoke object encapsulation.
- Pure functions: separate pure computation from stateful side-effects.
- Python `cytoolz` pipelines: use `cytoolz` (`pipe`, `map`, `filter`, `reduce`,
  `assoc`, `merge`, `groupby`, `valmap`) in Python to mimic Clojure-style
  immutable data manipulation instead of manual `for` loops.
- Polymorphism via data: favor multimethods and protocols over class
  inheritance.
- Schema à la carte: specify schemas flexibly where needed (e.g., Malli or
  Clojure Spec) without rigid compile-time class coupling.
- Idiom: 100 functions operating on 1 data structure are better than 10
  functions operating on 10 data structures.
- Semantic naming: make data keys and function names convey exact domain
  intent.
- Non-breaking evolution via accretion: design systems to evolve by adding
  new dispatches and optional keys without removing or tightening existing
  contracts (provide more, require less).
- Simplicity Score Gate: review evaluations must assess and report an
  objective Rich Hickey Simplicity Score (0-100, gate >= 80/100) checking 5
  un-complected dimensions: state/time separation, data/behavior decoupling,
  I/O vs pure logic isolation, mechanism vs policy, and module decoupling.
  Flag complected braids.
- REPL-driven development: prefer interactive evaluation via `clj-nrepl-eval`
  (`clj-nrepl-eval -p <port> "..."`) to explore data and verify logic. Always
  use `:reload` when requiring namespaces.
- Skill trigger: activate the `functional-coder` skill whenever designing,
  refactoring, or implementing functional code architectures.

## 2. Property-Based Testing (PBT) & Selective Execution

Every non-trivial transformation or data pipeline requires property-based
testing to ensure robustness across generated inputs:
- Unit tests verify specific known examples; PBT verifies fundamental
  invariants, algebraic properties, and round-trip consistency.
- Python ecosystem: require `hypothesis` for generating test strategies,
  fuzzing inputs, and shrinking failing cases.
- Clojure ecosystem: require `malli.generator` and `clojure.test.check` to
  validate schemas and generator-backed invariants.
- Selective test execution: during rapid iteration, run only targeted tests
  (specific vars, namespaces, or changed files, e.g., `pytest path::test_x` or
  single `deftest`/`defspec` over nREPL). Reserve full test suites for final
  verification gates.
- Consumer and subscriber contract tests: require targeted contract tests
  asserting that producer payload evolutions never break downstream legacy
  consumers or subscribers.
- Coverage requirement: unit tests alone are insufficient for core business
  logic, schema validations, serializers, or data transformations.

## 3. Asynchronous Swarm & Teamwork Model

Multi-agent coordination inside swarms must avoid synchronous lockstep and
idle waiting:
- Subteam Couple: each feature stream is owned by a paired subteam composed
  of an Executioner (`gemini-4-hydrogen-medium`) and a Reviewer/Auditor
  (`gemini-4-carbon-medium`).
- Controlled Blast Radius:
  - Executioners must strictly scope every commit and change to a minimal,
    explicit blast radius.
  - Work must remain confined to disjoint files and modules owned by the
    subteam; avoid silent cross-cutting modifications.
  - Prefer small atomic diffs over monolithic commits to simplify peer review
    and prevent regression cascades.
- Conflict-Free Git Topology:
  - Each subteam member operates in its own isolated working copy
    (`workspace: "share"`).
  - Dedicated branches: Executioner works on `subteam/<id>/work`; Reviewer
    audits and verifies on `subteam/<id>/review`.
  - Non-blocking pipeline: Executioner continuously commits increments to
    `subteam/<id>/work` and notifies Reviewer without pausing. Reviewer
    pulls and audits committed SHAs asynchronously.
- Shared nREPL Async Workflow:
  - Each subteam couple shares an nREPL port/session for fast interactive
    feedback.
  - Reviewer and Executioner evaluate pure forms, specs, and properties
    concurrently over nREPL without blocking each other.
  - Code mutations remain strictly version-controlled in git commits on
    `subteam/<id>/work`.
- Targeted Message Board Etiquette:
  - Structured message tags:
    - `[READY <sha>]` or `[READY <sha> nrepl:<port>]`: Executioner signals
      a new commit and optional active nREPL port ready for audit.
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
    Gemini 4 Carbon, Claude Opus 5.5, and GPT-OSS 120B) to audit logic,
    security, and architectural soundness from contrasting perspectives.
  - Simplicity scoring: panel members must compute and report the Simplicity
    Score (0-100, gate >= 80/100), blocking any code with unnecessary braids or
    hidden coupling.

## 4. Graphics and UI Wireframes

Whenever graphics, terminal displays, dashboards, or UI designs are
illustrated:
- Require explicit ASCII-art wireframes to visualize screen layouts,
  element hierarchies, and component placements.
- Ensure all ASCII diagrams conform strictly to the 80-character line width
  boundary.
- Use structured box-drawing characters or standard ASCII symbols (`+`, `-`,
  `|`, `[ ]`, `( )`) for clarity and deterministic rendering across terminals.

## 5. Readability & AST Code Limits

To maintain codebase readability and prevent bloated or complected code units,
all Clojure and Python source code must comply with AST-verified limits:
- Function length limit: maximum 20 lines of code per function definition
  (`defn`, `defn-`, `fn` in Clojure; `def`, `async def` in Python).
- File/module limit: maximum 500 lines per namespace or module file.
- Anti-golfing mandate: strictly forbid semicolon-chained Python statements,
  multi-top-level forms packed onto a single line, or dense multi-statement
  one-liners. Code must remain unrolled, explicit, and human-readable.
- Formatter precedence: always format Clojure code with `cljfmt` prior to
  evaluating AST or LSP static checks (`clj-kondo`, `clojure-lsp`,
  Python `ast`).
- Line length soft limit: 80 characters per line maximum (emits warnings;
  formatting is strongly enforced without breaking non-fatal builds).
- Lifecycle enforcement: automated via Antigravity hooks (`hooks.json` and
  `hooks/check_code_limits.py`) gating file edits and commit commands.

## 6. Problem-Solving & Skeptical Auditing

Activate the `problem-solving` skill for non-trivial debugging, design, and
root-cause analysis: pair George Polya's 4-step heuristics (*How to Solve It*)
with Dr. Steven Novella's cognitive bias and logical fallacy checks (*Skeptics'
Guide to the Universe*) to prevent premature conclusions.
