# Communication Protocols and Review Gates

This reference specifies message board etiquette, structured signaling tags,
selective testing procedures, and the multi-family Pro Ultimate Review Gate.

## 1. Message Board Communication Etiquette

The shared message board is broadcast to all swarm members. Every post consumes
context tokens across every agent that reads it. Careless chatter stalls swarms
and exhausts token budgets.

### Non-Negotiable Rules
1. **Targeted Doorbell Mentions**:
   - Always address the exact agent whose action is required (`@sw-review`).
   - Mentioning an agent wakes it from `swarm_wait`. Never tag peers who do not
     need to act on the message.
2. **Strict Prohibition on `@all`**:
   - Never post `@all` for status updates, routine handoffs, or check-ins.
   - Reserve `@all` solely for project-wide blockers or global state shifts.
3. **Reference by Sequence Number (`#<seq>`)**:
   - Reference prior messages using their sequence number (e.g., "per #14").
   - Do not quote or re-post large message blocks.
4. **No Empty Greetings or Acknowledgments**:
   - Never post "hello", "ready", "understood", or "working on it".
   - Every post must deliver a concrete state change, question, or result.

## 2. Structured Signaling Protocol

All agent handoffs utilize standardized uppercase tags:

- `[READY <sha>]` or `[READY <sha> nrepl:<port>]` (Executioner -> Reviewer):
  Payload: `<sha> [nrepl:<port>] <files>`. Increment committed and optional
  active nREPL port broadcast for rapid interactive audit.
- `[PASS <sha>]` (Reviewer -> Executioner):
  Payload: `<sha> <summary>`. Commit verified and passed all checks.
- `[FIX <sha>]` (Reviewer -> Executioner):
  Payload: `<sha> <details>`. Commit rejected; fixes required.
- `[BLOCK <sha>]` (Reviewer -> Executioner):
  Payload: `<sha> <reason>`. Critical issue blocking progression.
- `[done]` (Any -> Swarm/Coordinator):
  Payload: `<summary>`. Final task completion signal.

### Lifecycle of an Increment
```text
Executioner                                Reviewer
     |                                        |
     |--- [READY <sha> nrepl:<port>] -------->|  (Wakes & runs selective tests)
     |                                        |  (Evaluates forms over nREPL)
     | (authors next feature on work branch)  |--- [PASS <sha>] ------> Audited
     |                                        |
     |                                        |--or--
     |                                        |
     |<- [FIX <sha>] -------------------------|  (Queues amendment)
```

## 3. Selective Testing and Reviewer Audit Criteria

### Selective Test Execution Policy
Running full test suites or cold-boot runners on every single commit creates
severe development bottlenecks.
- **Fast Iteration**: Enforce selective test runs during incremental authoring:
  - In Clojure: evaluate single `deftest`, `defspec`, or schema checks over
    nREPL (`clj-nrepl-eval -p <port> "(run-test specific-var)"`).
  - In Python: execute targeted test paths (e.g., `pytest path::test_fn`).
- **Review Gates**: Full test suites, extensive property iterations (e.g.,
  1000+ generative runs), and `agy plugin validate . --strict` are reserved for
  pre-merge sign-off and the Ultimate Review Gate.

### Reviewer Audit Checklist
When reviewing an increment at `<sha>`, the Auditor evaluates:
1. **Line Length & Formatting**: Every line must be $\le 80$ characters.
2. **Functional Idioms**: Plain maps/data structures, pure functions,
   multimethods, schema à la carte, semantic naming.
3. **Property-Based Testing**: Non-trivial modules must include generative
   property tests (`hypothesis` or `test.check`/`malli`).
4. **Interactive REPL Verification**: Validate pure functions and schemas over
   the shared subteam nREPL port when applicable.
5. **Plugin Integrity**: Running `agy plugin validate . --strict` must pass
   without errors.

## 4. The Ultimate Review Gate

Prior to trunk integration or release, deliverables must pass through the
Ultimate Review Gate. This gate ensures verification across diverse reasoning
paradigms by engaging Pro-tier models from distinct provider families.

### Multi-Family Review Panel
A single model family may suffer from shared blind spots, hallucination
patterns, or stylistic biases. The panel brings together:
- **Google Gemini Family** (e.g., `gemini-4-hydrogen-medium` or Pro):
  Deep systemic context, tool integration, and schema verification.
- **Anthropic Claude Family** (e.g., `claude-opus-5.5`):
  Nuanced safety, formal logical reasoning, and refactoring rigor.
- **Open-Weights / GPT Family** (e.g., `gpt-oss-120b`):
  Independent algorithmic verification and adversarial invariant checks.

### Review Panel Execution Flow
1. **Branch Consolidation**: All passing increments on `subteam/<id>/work` are
   squashed or rebased to a candidate branch.
2. **Parallel Dispatch**: The swarm coordinator spawns panel auditors across
   each model family to independently review the complete diff.
3. **Exhaustive Validation**: Run the complete, non-selective test suite and
   property generators across all modules.
4. **Synthesis & Quorum**:
   - Each model submits an audit verdict.
   - Any consensus discrepancy triggers an investigation.
   - All tests, property suites, and strict plugin validations must pass
     unanimously before merging to `main`.
