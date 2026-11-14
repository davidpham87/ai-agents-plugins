# Harness Directives Plugin

Antigravity (`agy`) plugin collecting harness skills, rules, and directives
for functional coding, property-based testing, and asynchronous multi-agent
swarm collaboration.

## Structure

```text
.
├── plugin.json                 # Plugin manifest (required)
├── bb.edn                      # Babashka deps (malli, test.check, spec.alpha)
├── hooks.json                  # Antigravity lifecycle hooks configuration
├── hooks/
│   ├── check_code_limits.py    # AST & LSP code limit enforcement hook
│   └── test_check_code_limits_pbt.py # Hypothesis property-based tests
├── rules/
│   └── AGENTS.md               # Always-on directives & harness rules
└── skills/
    ├── functional-coder/       # Rich Hickey & functional programming skill
    │   └── SKILL.md            # Pure functions, data, multimethods, PBT
    ├── async-swarm-teamwork/   # Asynchronous multi-agent swarm runbook
    │   ├── SKILL.md            # Swarm execution patterns and workflows
    │   ├── scripts/            # Throughput & latency benchmarking harness
    │   └── references/         # In-depth runbooks and benchmark data
    ├── problem-solving/        # Polya heuristics & SGU skeptical auditing
    │   ├── SKILL.md            # 4-step workflow & bias/fallacy checks
    │   └── references/         # Polya steps, heuristics, biases, fallacies
    └── example-skill/
        └── SKILL.md            # On-demand skill template
```

## Included Directives and Skills

### 1. Harness Rules (`rules/AGENTS.md`)
Always-on directives loaded for every agent session in the workspace:
- **Functional Coder Directives**: Rich Hickey principles emphasizing plain
  data (maps/sets/vectors), pure functions, polymorphism via data
  (multimethods), schema à la carte (Malli/Spec), semantic naming, and
  interactive REPL evaluation via `clj-nrepl-eval`.
- **Property-Based Testing & Selective Execution**: Mandates generative
  testing via `hypothesis` (Python) and `malli`/`test.check` (Clojure), with
  selective test runs during rapid inner-loop iteration.
- **Asynchronous Swarms**: Outlines paired subteam couples (Executioner +
  Reviewer), controlled blast radius, non-breaking evolution via accretion,
  consumer contract tests, non-blocking Git flows, shared nREPL sessions,
  targeted message board etiquette, and the multi-family Pro Ultimate Gate.
- **Simplicity Score Gate**: Evaluates code along 5 un-complected dimensions
  (state/time, data/logic, decoupling) to prevent complected braids.
- **Readability & AST Code Limits**: Enforces <= 20 lines per function, <= 500
  lines per file, anti-golfing rules, and `cljfmt` pre-formatting via hooks.
- **Graphics and UI Wireframes**: Mandates ASCII-art wireframes for all visual
  or UI layouts, constrained to 80 characters per line.

### 2. Functional Coder Skill (`skills/functional-coder/`)
On-demand skill guiding system design and implementation following functional
paradigms:
- Decoupling data from behavior.
- Designing pure transformation pipelines and transducers.
- Implementing generative property checks and domain schemas.

### 3. Async Swarm Teamwork Skill (`skills/async-swarm-teamwork/`)
On-demand operational runbook and toolset for multi-agent swarms:
- **Subteams & Git (`references/01-async-subteams-and-git.md`)**:
  Guidelines for Executioner (`gemini-4-hydrogen-medium`) and Reviewer
  (`gemini-4-carbon-medium`) couples, `workspace: "share"` isolation,
  dedicated `subteam/<id>/work` branches, and conflict-free pipelines.
- **Communication & Review (`references/02-communication-and-review.md`)**:
  Structured board tags (`[READY]`, `[PASS]`, `[FIX]`, `[BLOCK]`, `[done]`),
  targeted doorbell notifications, Rich Hickey Simplicity Score Gate, and the
  multi-family Pro Ultimate Review Gate (Gemini, Claude, GPT).
- **Benchmarking Throughput**:
  Harness scripts and empirical reports measuring pipelined async speedups
  over synchronous request-response lockstep.

### 4. Problem-Solving Skill (`skills/problem-solving/`)
On-demand reasoning skill pairing George Polya (*How to Solve It*) with Dr.
Steven Novella (*The Skeptics' Guide to the Universe*):
- **Polya Steps & Heuristics (`references/01-*.md`, `02-*.md`)**:
  Structured 4-phase problem solving and classic heuristics (working backwards,
  auxiliary problems, generalization, invariants).
- **Skeptical Auditing (`references/03-*.md`, `04-*.md`)**:
  Cognitive bias countermeasures, logical fallacy detection, falsifiability,
  and Occam's razor engineering checklists.

### 5. Lifecycle Hooks (`hooks.json` & `hooks/`)
Automated Antigravity lifecycle hooks enforcing code limits:
- **`PostToolUse`**: Validates file line limits and code readability after
  `write_file` or `edit_file`.
- **`PreToolUse`**: Enforces code limits and gates `git commit` commands,
  preventing complected or golfed code from entering version control.

## Validate and Install

Validate the plugin structure with the Antigravity CLI:

```sh
agy plugin validate . --strict
```

Install the plugin locally:

```sh
agy plugin install .
```
