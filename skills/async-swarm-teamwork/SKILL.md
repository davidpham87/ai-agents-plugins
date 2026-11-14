---
name: async-swarm-teamwork
description: >-
  Runbook and patterns for asynchronous, conflict-free multi-agent swarms.
  Covers executioner-reviewer subteams, git share pipelines, shared nREPL
  sessions, selective testing, board etiquette, benchmarking async vs sync
  throughput, and multi-family Pro review gates.
---

# Async Swarm Teamwork Skill

This skill defines the operational runbook and collaboration patterns for
high-throughput, asynchronous agent swarms in Antigravity (`agy`).

## When to Activate

Activate this skill whenever:
- Designing or spinning up a multi-agent swarm with specialized roles.
- Coordinating paired subteams (Executioner + Reviewer/Auditor).
- Establishing conflict-free Git workflows across parallel workspaces.
- Running non-blocking commit-and-audit verification loops.
- Sharing interactive nREPL evaluation ports across subteam agents.
- Enforcing selective test execution during iterative fast development.
- Benchmarking asynchronous vs synchronous swarm performance.
- Conducting an Ultimate Review Gate using heterogeneous Pro model families.

## Architecture Overview

```text
+-----------------------------------------------------------------+
|                       Coordinator Swarm                         |
+-----------------------------------------------------------------+
       |                                           |
       v                                           v
+-------------------------------+   +-------------------------------+
| Subteam Alpha                 |   | Subteam Beta                  |
| - Executioner (Flash)         |   | - Executioner (Flash)         |
|   branch: subteam/alpha/work  |   |   branch: subteam/beta/work   |
|   commits [READY <sha>]       |   |   commits [READY <sha>]       |
| - Reviewer (Hydrogen)         |   | - Reviewer (Hydrogen)         |
|   branch: subteam/alpha/review|   |   branch: subteam/beta/review |
|   audits [PASS|FIX <sha>]     |   |   audits [PASS|FIX <sha>]     |
| - Shared subteam nREPL port   |   | - Shared subteam nREPL port   |
|   evaluates pure forms async  |   |   evaluates pure forms async  |
+-------------------------------+   +-------------------------------+
       |                                           |
       +--------------------+----------------------+
                            v
+-----------------------------------------------------------------+
|                      Ultimate Review Gate                       |
|   Multi-family Pro Panel: Gemini 4 Hydrogen, Claude Opus 5.5,   |
|                       and GPT-OSS 120B                          |
+-----------------------------------------------------------------+
```

### 1. Paired Subteams (Executioner + Reviewer)
- **Executioner** (`gemini-3.8-flash-medium`): Rapid, iterative code author.
  Generates implementations, property tests, and granular git commits.
- **Reviewer / Auditor** (`gemini-4-hydrogen-medium`): Thorough code and
  schema auditor. Inspects commits, tests properties, and enforces rules.

### 2. Isolated Git Topologies & Shared nREPL Workflows
- Every subteam agent operates in a dedicated working copy
  (`workspace: "share"`), preventing uncommitted collisions.
- Clear branching conventions keep authoring and review decoupled:
  `subteam/<id>/work` and `subteam/<id>/review`.
- Subteams share a persistent nREPL port/session (`clj-nrepl-eval`) for pure
  form evaluation, schema checking, and REPL-driven development without
  blocking each other.

### 3. Non-Blocking Commit Pipeline & Selective Test Execution
- The Executioner commits each functional increment and immediately posts
  `@<reviewer> [READY <sha> nrepl:<port>] <files>`.
- The Executioner does NOT block or sleep waiting for approval; it moves
  straight into the subsequent increment.
- Selective test runs (targeted vars, namespaces, or changed test files) are
  enforced during fast iteration; full-suite execution is reserved for gates.
- The Reviewer audits each SHA asynchronously.

### 4. Board Etiquette & Targeted Signaling
- Direct `@mentions` only: wake only the intended recipient.
- Standard protocol tags: `[READY <sha> nrepl:<port>]`, `[PASS <sha>]`,
  `[FIX <sha>]`, `[BLOCK <sha>]`, and `[done]`.
- No `@all` noise for routine status; cite `#<seq>` for message history.

## Detailed Runbooks & References

- Subteams, git shares, nREPL workflow, and conflict resolution:
  See [01-async-subteams-and-git.md](
  ./references/01-async-subteams-and-git.md).
- Messaging protocol, selective testing, and multi-family Pro review gate:
  See [02-communication-and-review.md](
  ./references/02-communication-and-review.md).
- Benchmarking throughput & latency (async pipelined vs synchronous lockstep):
  See the benchmarking harness script:
  [benchmark_async_vs_sync.py](./scripts/benchmark_async_vs_sync.py)
  and the benchmark evaluation report:
  [benchmark-report.md](./references/benchmark-report.md).

## Operational Checklist

1. [ ] Spawn subteam pairs with `workspace: "share"` and assigned roles.
2. [ ] Check out isolated branches (`subteam/<id>/work`).
3. [ ] Initialize shared subteam nREPL session if developing Clojure code.
4. [ ] Author code following Rich Hickey functional directives and PBT.
5. [ ] Execute selective tests during rapid inner loop iteration.
6. [ ] Make granular commits and broadcast `[READY <sha>]` to reviewer.
7. [ ] Triage reviewer feedback (`[FIX <sha>]`) and apply amendments.
8. [ ] Convene heterogeneous multi-model Pro panel for the Ultimate Review.
9. [ ] Validate full test suites and plugin (`agy plugin validate . --strict`).
