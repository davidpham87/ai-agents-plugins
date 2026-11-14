# Asynchronous Subteams and Git Architecture

This guide details the topology, branching strategy, shared nREPL workflow,
and non-blocking Git mechanisms that enable high-velocity multi-agent swarms.

## 1. Rationale for Subteam Pairs

Complex software engineering tasks stall when a single agent alternates
between authoring code and self-critiquing, or when multiple agents attempt
to modify identical files simultaneously.

To optimize token efficiency and wall-clock latency, agents are paired into
specialized subteams:
- **Executioner** (`gemini-3.8-flash-medium`):
  Optimized for rapid generation, refactoring, and test writing. Authors
  focused increments and makes atomic Git commits.
- **Reviewer / Auditor** (`gemini-4-hydrogen-medium`):
  Optimized for deep architectural reasoning, edge-case detection, and
  property verification. Audits committed SHAs without interrupting authoring.

This model split pairs low-cost, fast generation with rigorous scrutiny,
preventing cognitive drift and costly synchronous bottlenecks.

## 2. Git Share Topology (`workspace: "share"`)

Never allow parallel agents to operate within a shared working directory
(`workspace: "inherit"`). Doing so causes:
- Interleaved uncommitted edits that break build harnesses.
- Index locking collisions during simultaneous Git commands.
- Lost updates and race conditions during file overwrites.

### The Share Mechanism
When spawning agents with `workspace: "share"`, Antigravity provisions an
isolated Git worktree sharing the same underlying Git repository object
store (`.git` database). This gives each agent:
1. An independent working tree on disk.
2. An isolated Git index (staging area) and `HEAD`.
3. Instantaneous local visibility of committed Git objects and branches.

## 3. Branching Strategy & Lifecycle

Each subteam adopts a standardized branch convention:
- `subteam/<id>/work`: Branch where the Executioner lands incremental commits.
- `subteam/<id>/review`: Branch where the Reviewer verifies or experiments.

### Executioner Lifecycle
1. Create and switch to `subteam/<id>/work` from the agreed baseline branch.
2. Implement an incremental unit of functionality or test coverage.
3. Validate locally with selective tests and linter checks.
4. Create an atomic Git commit:
   ```sh
   git commit -m "feat(module): implement data transformation"
   ```
5. Extract the commit SHA (`git rev-parse HEAD`).
6. Post `@<reviewer> [READY <sha> nrepl:<port>] <files>` to the board.
7. Immediately proceed to the next unit of work without blocking.

### Reviewer Lifecycle
1. Maintain or update `subteam/<id>/review` pointing to the Executioner's
   latest announced SHA:
   ```sh
   git checkout -B subteam/<id>/review <sha>
   ```
2. Inspect diffs against the prior verified commit:
   ```sh
   git diff <last-pass-sha> <sha>
   ```
3. Run selective property checks or evaluate expressions over nREPL.
4. Validate plugin integrity:
   ```sh
   agy plugin validate . --strict
   ```
5. If valid, post `@<executioner> [PASS <sha>]`.
6. If defects or style violations exist, post `@<executioner> [FIX <sha>]`
   identifying exact file paths, line numbers, and required corrections.

## 4. Shared nREPL Async Workflow

To achieve instant feedback loops without waiting for file writes or slow
process initialization, Clojure subteams adopt a shared nREPL workflow:

### Discovery and Connection
- The subteam identifies active nREPL ports using:
  ```sh
  clj-nrepl-eval --discover-ports
  ```
- The Executioner includes the port in handoff messages:
  `[READY <sha> nrepl:<port>]`.

### Concurrent Interactive Evaluation
- Both Executioner and Reviewer connect to the shared nREPL session via:
  ```sh
  clj-nrepl-eval -p <port> "<clojure-code>"
  ```
- Pure functions, malli schemas, and generative property checks are
  evaluated interactively and concurrently over nREPL without contention.
- Because functions and schemas are pure data and pure logic, concurrent
  queries never block each other.
- All persistent source code modifications remain strictly isolated to Git
  commits on `subteam/<id>/work`, preventing workspace corruption.

## 5. Conflict Avoidance & Blast Radius Management

To guarantee zero merge conflicts and smooth multi-subteam parallelism:
- **Controlled Blast Radius**:
  - Executioners must scope every commit to a minimal, explicit blast radius.
  - Modifications must stay confined to disjoint files and modules owned by
    the subteam; never introduce silent cross-cutting edits.
  - Small, atomic diffs ensure reviewer comprehension and rapid turnaround.
- **Strict File Ownership**: Subteams must be assigned disjoint sets of files.
  For example, Subteam A owns `rules/`, Subteam B owns `skills/foo/`, Subteam
  C owns `skills/bar/`.
- **Read-Only Peer References**: If Subteam A needs functionality written by
  Subteam B, it imports or references the agreed contract without editing
  Subteam B's files.
- **Atomic Squashing & Rebase**: When a subteam completes all increments, its
  feature branch is rebased cleanly on top of the main trunk prior to final
  integration.

## 6. Non-Blocking vs Synchronous Throughput

In traditional synchronous workflows, an author must pause and wait for code
review before starting subsequent tasks. If review takes $T_{rev}$ and authoring
takes $T_{auth}$, sequential turnaround time for $N$ tasks scales as:
$$T_{sync} = N \times (T_{auth} + T_{rev})$$

Under the non-blocking pipeline pattern, the Executioner continues authoring
step $k+1$ while the Reviewer verifies step $k$:
$$T_{async} \approx \max(N \times T_{auth}, N \times T_{rev}) + T_{latency}$$

For empirical measurements and mathematical modeling comparing synchronous
ping-pong to pipelined asynchronous subteams:
- Benchmark execution script:
  [benchmark_async_vs_sync.py](../scripts/benchmark_async_vs_sync.py)
- Full benchmark report and data:
  [benchmark-report.md](./benchmark-report.md)
