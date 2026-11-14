# Practical Problem-Solving Techniques

Polya's heuristics excel when a problem's boundaries are crisp. Real-world
engineering also demands tools for questioning hidden assumptions, managing
uncertainty, finding bottlenecks, and deciding what *not* to solve now.

## Quick-Selection Matrix

```
+-----------------------------------------+------------------------------------+
| Symptom / Stuck State                   | Recommended Technique              |
+-----------------------------------------+------------------------------------+
| Cargo-culting bloated legacy patterns   | First Principles Decomposition     |
| Plan feels suspiciously optimistic      | Inversion & Pre-Mortem Thinking    |
| Local tweaks give zero system speedup   | Theory of Constraints (Bottleneck) |
| High unknown risk; stalling on design   | Time-Boxed Spikes & Tracer Bullets |
| Vague grasp; hand-waving specs or bugs  | Feynman Teach-Back & Rubber Duck   |
| Anchored on one familiar design option  | Morphological Matrix Mapping       |
| Too many problems; unclear priority     | Dual Framing & Cost-of-Delay       |
+-----------------------------------------+------------------------------------+
```

---

## 1. First Principles Decomposition

Strip away inherited conventions and "best practices" until only verifiable
physical, mathematical, or business constraints remain, then rebuild from there.

* **When to use**:
  Proposed architectures feel unnecessarily heavy, vendor patterns dictate
  expensive complexity, or constraints sound like habit rather than necessity.
* **Practical steps**:
  1. List every assumption embedded in the current proposal (e.g., "needs a
     distributed cache", "must be real-time event streaming").
  2. Test each assumption against hard truths: latency physics, data volume,
     consistency math, legal rules, or budget caps.
  3. Discard any requirement lacking a hard backing and synthesize the
     simplest design satisfying what remains.
* **Concrete example**:
  A team plans Kafka, an ETL worker, and a warehouse for an internal dashboard.
  Checking hard constraints (400k rows/day, 5-minute freshness SLA) shows a
  single PostgreSQL materialized view satisfies everything in 35 lines of SQL.
* **Common pitfall**:
  Reinventing solved low-level primitives (cryptography, consensus) from
  scratch when you only needed to question high-level system topology.

---

## 2. Inversion & Pre-Mortem Thinking

Instead of asking only how a design succeeds, solve backwards from plausible
catastrophic failures and build structural defenses before writing features.

* **When to use**:
  High-stakes launches, schema migrations, security boundaries, or anywhere
  optimism bias hides irreversible failure modes.
* **Practical steps**:
  1. Imagine the system failed severely three months after release.
  2. Enumerate every concrete technical, operational, and human path that
     could have caused that failure.
  3. Invert each failure mode into an explicit invariant, guardrail, circuit
     breaker, or rollback path.
* **Concrete example**:
  Before a zero-downtime database migration, a pre-mortem asks "How do we lose
  or corrupt writes?" It surfaces dual-write skew and irreversible drops,
  leading to expand-contract phases, shadow-read diffs, and a kill-switch flag.
* **Common pitfall**:
  Devolving into unfocused pessimism or infinite defensive scope; constrain
  guardrails to high-severity, realistic failure paths.

---

## 3. Theory of Constraints & Bottleneck Analysis

Every system's throughput or latency is governed by its single tightest
constraint. Improving any non-bottleneck stage yields zero net improvement.

* **When to use**:
  Performance tuning, CI pipeline slowdowns, or delivery stalls where prior
  optimizations barely moved end-to-end metrics.
* **Practical steps**:
  1. **Identify**: Measure end-to-end stage timings or queue depths to find
     the single limiting factor.
  2. **Exploit**: Eliminate wasted work at that exact constraint first.
  3. **Subordinate**: Pace upstream producers so they do not flood the
     bottleneck with excess retries or queued work.
  4. **Elevate & Repeat**: Add capacity only if needed, then re-measure as
     the bottleneck shifts elsewhere.
* **Concrete example**:
  An endpoint takes 820ms. Caching JSON formatting saves 5ms, while an
  unindexed `JOIN` consumes 750ms. Measuring stages pinpoints the query;
  adding a composite index drops total latency to 75ms, shifting focus to I/O.
* **Common pitfall**:
  Optimizing an easy, familiar component off the critical path—adding code
  complexity without changing user-visible latency or throughput.

---

## 4. Time-Boxed Spikes & Tracer Bullets

Under high uncertainty, buy empirical knowledge cheaply with bounded code
experiments rather than debating hypotheticals on a whiteboard.

* **When to use**:
  Integrating unfamiliar APIs, verifying runtime limits, or facing analysis
  paralysis over architectural trade-offs.
* **Practical steps**:
  1. Formulate one falsifiable question ("Can library X parse 50MB XML under
     128MB RAM?").
  2. Choose a **Spike** (throwaway prototype deleted after learning) or a
     **Tracer Bullet** (minimal permanent end-to-end skeleton across layers).
  3. Enforce a strict time-box (e.g., 90 minutes). Stop when time expires and
     decide from observed measurements.
* **Concrete example**:
  Unsure whether corporate proxies drop idle WebSockets, a 60-minute spike
  deploys an echo endpoint to staging. Logs prove connections drop at 60s,
  revealing the heartbeat requirement before protocol work begins.
* **Common pitfall**:
  Shipping a throwaway spike straight to production without tests, error
  handling, or clean boundaries.

---

## 5. Feynman Teach-Back & Rubber Ducking

Force hidden mental gaps into the open by explaining the mechanism or bug in
plain, jargon-free language step by step.

* **When to use**:
  You feel "90% sure" how a module works, requirements feel slippery, or a bug
  resists hours of silent code reading.
* **Practical steps**:
  1. Narrate the exact causal chain aloud or in plain prose for a listener
     with zero context (a teammate, note, or rubber duck).
  2. Forbid hand-waving phrases ("somehow", "it syncs", "magically works").
  3. Stop at every hesitation or jargon leap—that gap marks your unverified
     assumption or the actual defect.
* **Concrete example**:
  Explaining an auth bug—"the refresh handler updates the token, then queued
  requests retry with the new... wait, queued closures captured the old
  header"—exposes the stale closure mid-sentence.
* **Common pitfall**:
  Giving a high-level summary instead of tracing concrete inputs, states, and
  transitions one step at a time.

---

## 6. Morphological Matrix / Option-Space Mapping

Systematically map independent design dimensions into a grid so you explore
clean combinations instead of anchoring on the first familiar architecture.

* **When to use**:
  Designing multi-part systems where several orthogonal choices interact and
  debates reduce to two polarized extremes.
* **Practical steps**:
  1. Split the problem into 3-5 independent axes (e.g., Queue, Ordering,
     Retry Strategy).
  2. List 2-4 realistic options per axis in a matrix.
  3. Prune incompatible pairs, then evaluate 2-3 coherent paths across rows
     against your real constraints.
* **Concrete example**:
  Webhook delivery options:
  * **Storage**: `[Postgres table, Redis Streams, SQS]`
  * **Ordering**: `[None, Per-tenant key, Global]`
  * **Failure**: `[Drop, Exponential backoff, Dead-letter queue]`
  Combining `[Postgres table + Per-tenant key + Dead-letter queue]` delivers
  durability without operating a new message broker.
* **Common pitfall**:
  Trying to benchmark every theoretical cell combination instead of pruning
  mutually incompatible choices immediately.

---

## 7. Dual Framing & Cost-of-Delay / Triage

Decide deliberately which problems deserve solving now, which need cheap
containment, and which should be left unsolved.

* **When to use**:
  Backlogs grow faster than capacity, incidents compete with roadmap work, or
  engineers polish low-impact internals while urgent risks compound.
* **Practical steps**:
  1. Apply **Dual Framing**: compare "Value gained by solving now" against
     "Exact cost if we defer, wrap, or delete this problem."
  2. Rank work by **CD3** (Cost of Delay Divided by Duration): urgency times
     weekly impact, divided by implementation effort.
  3. Assign each item to *Solve Now*, *Contain Cheaply*, or *Defer* with an
     explicit quantitative trigger to revisit.
* **Concrete example**:
  A team weighs rewriting a clunky monthly billing script (5 days effort,
  easy 10-minute manual check) against rising checkout timeouts. Triage wraps
  the script in an alert (30 minutes) and targets the timeouts first.
* **Common pitfall**:
  Prioritizing the loudest complaint or most intellectually interesting puzzle
  over the highest cost of delay.
