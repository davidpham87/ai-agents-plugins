# Harness Directives Plugin

Antigravity (`agy`) plugin collecting harness skills, rules, and directives
for functional coding, property-based testing, and asynchronous multi-agent
swarm collaboration.

## Structure

```text
.
├── plugin.json                 # Plugin manifest (required)
├── rules/
│   └── AGENTS.md               # Always-on directives & harness rules
└── skills/
    ├── functional-coder/       # Rich Hickey & functional programming skill
    │   └── SKILL.md            # Pure functions, data, multimethods, PBT
    ├── async-swarm-teamwork/   # Asynchronous multi-agent swarm runbook
    │   ├── SKILL.md            # Swarm execution patterns and workflows
    │   ├── scripts/            # Throughput & latency benchmarking harness
    │   └── references/         # In-depth runbooks and benchmark data
    └── example-skill/
        └── SKILL.md            # On-demand skill template
```

## Included Directives and Skills

### 1. Harness Rules (`rules/AGENTS.md`)
Always-on directives loaded for every agent session in the workspace:
- **Functional Coder Directives**: Rich Hickey principles emphasizing plain
  data (maps/sets/vectors), pure functions, polymorphism via data
  (multimethods), schema à la carte (Malli/Spec), and semantic naming.
- **Property-Based Testing (PBT)**: Mandates generative testing via
  `hypothesis` (Python) and `malli`/`test.check` (Clojure) over unit-only tests.
- **Asynchronous Swarms**: Outlines paired subteam couples (Executioner +
  Reviewer), non-blocking Git commit/audit flows, targeted message board
  etiquette, and the multi-family Pro Ultimate Review Gate.
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
  Guidelines for Executioner (`gemini-3.8-flash-medium`) and Reviewer
  (`gemini-4-hydrogen-medium`) couples, `workspace: "share"` isolation,
  dedicated `subteam/<id>/work` branches, and conflict-free pipelines.
- **Communication & Review (`references/02-communication-and-review.md`)**:
  Structured board tags (`[READY]`, `[PASS]`, `[FIX]`, `[BLOCK]`, `[done]`),
  targeted doorbell notifications, and the multi-family Pro Ultimate Review
  Gate (Gemini 4 Hydrogen, Claude Opus 5.5, GPT-OSS 120B).
- **Benchmarking Throughput**:
  Harness scripts and empirical reports measuring pipelined async speedups
  over synchronous request-response lockstep.

## Validate and Install

Validate the plugin structure with the Antigravity CLI:

```sh
agy plugin validate . --strict
```

Install the plugin locally:

```sh
agy plugin install .
```
