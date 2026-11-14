# Practical Diagnostic and Debugging Tactics

> "Debugging is twice as hard as writing the code in the first place.
> Therefore, if you write the code as cleverly as possible, you are, by
> definition, not smart enough to debug it."
> — Brian W. Kernighan

Polya's Understand, Plan, Execute, and Look Back loop stalls during debugging
when engineers guess causes from memory instead of systematically shrinking
the search space. These seven tactics turn skeptical hygiene into concrete
moves that isolate faults fast and verify fixes without self-deception.

---

## Diagnostic Decision Flow

Use this flow to pick the right tactic before editing production code:

```text
Symptom Observed (Polya Phase 1: Understand)
  |
  v
Can you reproduce it reliably?
  |-- NO --> Timeline & State Reconstruction (logs, monotonic IDs)
  |            |--> Compare failing vs passing runs (Diff Diagnosis)
  v
  YES
  |
  v
Shrink the trigger: Minimal Reproducible Example (MRE) / Delta Debug
  |
  v
Where does the unknown boundary live?
  |-- Time / commits -----> git bisect (known-good .. known-bad)
  |-- Pipeline / module --> Wolf Fence (probe invariants at midpoint)
  |-- Env / config -------> Differential Diagnosis (good vs bad delta)
  |
  v
Form competing hypotheses (Polya Phase 2: Plan)
  |
  v
Controlled One-Variable Experiment (predict -> falsify)
  |
  v
Fix verified? --> Branching 5 Whys (map contributing causes & guards)
```

---

## 1. Binary Search / Bisection and `git bisect`

Halve an ordered search space repeatedly (`O(log n)` checks) instead of
scanning commits, lines, or records sequentially. Counters **Anchoring** and
the **Availability Heuristic** by letting evidence locate the fault.

* **When to use**: A regression appeared between a known-good state and a
  broken state, or a bug hides inside a large ordered range (commit history,
  sorted dataset, configuration flags, or deployment sequence).
* **Practical steps**:
  1. Build a deterministic pass/fail oracle (script, unit test, or benchmark).
  2. Verify both endpoints directly: confirm `good` passes and `bad` fails.
  3. Probe the exact midpoint; discard the half that preserves the invariant.
  4. For history searches, automate with `git bisect start <bad> <good>` and
     `git bisect run <oracle-script>`.
* **Concrete example**: Checkout latency doubles over two weeks. You verify a
  14-day-old tag passes a 10-second replay script, then run `git bisect run
  ./check-latency.sh`. Across 1,024 commits, 10 automated runs pinpoint the
  exact commit that removed a database index hint.
* **Trap to avoid**: Running `git bisect` with stale build artifacts or caches,
  or bisecting a flaky test where false passes send the search into the wrong
  half of history.

---

## 2. Wolf Fence Debugging

"Build a fence across Alaska; wait to hear which side the wolf howls on."
Places invariant probes at midpoints along an execution path, operationalizing
Polya's rule to check every intermediate condition.

* **When to use**: State or data is corrupted somewhere inside a multi-stage
  pipeline, call chain, or distributed flow without an obvious commit boundary.
* **Practical steps**:
  1. State the exact invariant that holds at entry and fails at exit.
  2. Place a non-invasive assertion, breakpoint, or structured log at the
     midpoint of the data path.
  3. Run once to prove whether the invariant breaks before or after the fence.
  4. Move the fence to the midpoint of the guilty half until a single boundary
     or function is trapped.
* **Concrete example**: An invoice PDF prints `NaN` for the total. You assert
  `Number.isFinite(total)` right after tax calculation (the midpoint of
  `Cart -> Tax -> Discount -> PDF`). The assertion passes, trapping the bug in
  `Discount -> PDF`; one more fence exposes a `0 / 0` ratio on free bundles.
* **Trap to avoid**: Logging vague breadcrumbs ("reached step 3") instead of
  checking the domain invariant, or discarding the final probe instead of
  promoting it to a permanent assertion or unit test.

---

## 3. Minimal Reproducible Example (MRE) and Delta Debugging

Shrink a noisy, failing input or setup down to the smallest standalone trigger.
Applies Polya's specialization heuristic and neutralizes **Anchoring** on
irrelevant surrounding details.

* **When to use**: Failures occur only inside large payloads, sprawling
  configs, or slow integration suites where noise obscures the mechanism.
* **Practical steps**:
  1. Capture the exact failing input, random seed, and failure signature.
  2. Delete half the input, modules, or config keys; keep the smaller version
     only if it reproduces the *identical* failure signature.
  3. Repeat binary chunk removal (delta debugging) until removing any single
     line, field, or call causes the bug to disappear.
  4. Freeze the minimal trigger into a fast, self-contained regression test.
* **Concrete example**: A 4 MB JSON import crashes the parser. Halving the
  record array reduces 12,000 items to 1, and stripping keys leaves
  `{"note": "\uD800"}`—an unpaired UTF-16 surrogate that crashes normalization.
* **Trap to avoid**: Over-trimming until a *different* error appears (such as a
  missing-field validation error) and mistaking the new failure for your MRE.

---

## 4. Differential Diagnosis

Compare a concrete known-good execution against a concrete broken execution
side by side. Enforces **Neuropsychological Humility** by checking live
artifacts rather than trusting memory that two environments "are identical."

* **When to use**: A defect manifests only in one environment, tenant, OS, or
  time window ("works on my machine" or "passes in staging, fails in prod").
* **Practical steps**:
  1. Capture primary artifacts for both one passing run and one failing run
     (env vars, lockfiles, runtime flags, schema versions, full traces).
  2. Generate an explicit mechanical `diff` rather than eyeballing configs.
  3. Separate expected variance (timestamps, hostnames, IDs) from causal
     candidates (library patch versions, locales, pool limits, feature flags).
  4. Port one candidate difference at a time until the behavior flips.
* **Concrete example**: Report exports corrupt UTF-8 characters only in
  production. Diffing `env` and `locale` outputs between staging and prod
  exposes `LC_ALL=C` in prod versus `en_US.UTF-8` in staging.
* **Trap to avoid**: Stopping at the first superficial difference or comparing
  deployment templates instead of inspecting the actual live runtime state.

---

## 5. Timeline and State-Transition Reconstruction

Reassemble interleaved events and state mutations onto one ordered timeline.
Directly counters **Post Hoc** illusions and **Patternicity** when debugging
concurrent or distributed behavior.

* **When to use**: Race conditions, flaky tests, duplicate deliveries, or
  cascading timeouts involving multiple threads, workers, or services.
* **Practical steps**:
  1. Gather logs, metrics, and database/queue audits tied to one correlation
     or entity ID.
  2. Normalize timestamps to UTC and pair them with monotonic sequence IDs
     because unsynchronized host clocks skew ordering.
  3. Plot a unified table: `Time/Seq | Actor | Event | State Before -> After`.
  4. Flag impossible transitions, stale reads, and missing atomic guards.
* **Concrete example**: Customers are double-charged during gateway slowdowns.
  Aligning webhook logs, retry workers, and DB row versions shows Worker B
  read `status=PENDING` 12 ms before Worker A committed `status=PAID`,
  exposing a missing compare-and-swap transition check.
* **Trap to avoid**: Reading one service's logs in isolation or treating
  wall-clock log order across separate machines as guaranteed causal order.

---

## 6. Branching 5 Whys / Cause-Effect Trees

Map the tree of jointly necessary conditions behind a failure instead of
forcing a single linear chain. Implements Polya's Look Back phase while
preventing **Hindsight Bias** and the single-root-cause fallacy.

* **When to use**: Complex outages, recurring regressions, or postmortems where
  a bug needed multiple weak defenses to become user-visible.
* **Practical steps**:
  1. Place the verified symptom at the root node using primary evidence.
  2. Ask "What conditions were *jointly required* for this outcome?"—branch
     whenever a trigger, a missing guardrail, and a detection gap align.
  3. Trace each branch until it reaches a concrete technical, design, or
     process weakness (never stop at "engineer forgot").
  4. Assign independent mitigations across branches so breaking any single
     path prevents recurrence.
* **Concrete example**: A schema migration stalls checkout. Branch A: migration
  omitted a lock timeout (trigger). Branch B: staging lacked realistic lock
  contention (test gap). Branch C: health checks missed blocked DB pools
  (observability gap). Fixing all three hardens the whole system.
* **Trap to avoid**: Telling a neat linear story ("5 Whys" in one straight
  line) that satisfies **Confirmation Bias** while leaving sibling gaps open.

---

## 7. Controlled One-Variable Experiments

Test one hypothesis at a time against an explicit falsifying prediction.
Operationalizes scientific **Falsifiability** inside Polya's Plan/Execute
loop and stops **Sunk Cost** patching.

* **When to use**: Before committing to a fix, tuning performance knobs, or
  adjudicating between competing root-cause theories.
* **Practical steps**:
  1. Write down your hypothesis and what result would *disprove* it: "If X
     causes Y, changing only X must yield Z; otherwise X is false."
  2. Change strictly one variable while pinning inputs, seed, and environment.
  3. Record raw measurements before interpreting or tuning further.
  4. Revert immediately if falsified; never stack unverified tweaks.
* **Concrete example**: Suspecting DB pool exhaustion causes 504 timeouts, you
  double `max_pool_size` under identical replay traffic and predict 504s drop
  to zero. Timeouts persist while CPU hits 100%, falsifying the pool theory
  and pointing directly to a catastrophic backtracking regex.
* **Trap to avoid**: Tweaking three configs, restarting pods, and flushing a
  cache simultaneously; if the symptom clears, **Post Hoc** reasoning tricks
  you into keeping cargo-cult changes.
