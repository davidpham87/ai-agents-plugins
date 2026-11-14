# Skeptical Cognitive Biases and Countermeasures

> "The first principle of skepticism is neuropsychological humility: knowing
> how easily the human brain fools itself."
> — Dr. Steven Novella, *The Skeptics' Guide to the Universe*

Even brilliant engineers fall prey to systematic cognitive illusions. Under
time pressure, our brains construct plausible stories, see patterns in noise,
and defend broken hypotheses. Scientific skepticism provides concrete
countermeasures.

---

## 1. Neuropsychological Humility

Human perception and memory are reconstructive, not video recordings.
* **Trap**: Trusting memory of what a config file, log, or stack trace "said"
  yesterday.
* **Countermeasure**: Always verify primary artifacts directly. Re-read the
  exact file, re-run the command, and record raw outputs.

## 2. Confirmation Bias

Seeking, interpreting, and remembering evidence that supports our favored
hypothesis while ignoring or explaining away contradicting data.
* **Trap**: Reading only the log lines that match your pet root-cause theory.
* **Countermeasure**: Actively design falsification tests. Ask: "What
  observation would *disprove* my current hypothesis?"

## 3. Availability Heuristic

Judging the probability of a bug or bottleneck by how vividly or recently a
similar issue comes to mind.
* **Trap**: Blaming Redis or DNS for every timeout because last week's outage
  involved Redis.
* **Countermeasure**: Measure base rates and profile the actual system
  before guessing where latency or failures live.

## 4. Post Hoc (Ergo Propter Hoc)

Assuming that because event B followed event A, A must have caused B.
* **Trap**: "I restarted the worker and the error stopped, so the worker had
  a memory leak" (when an upstream rate limit simply expired).
* **Countermeasure**: Demand a reproducible causal mechanism or controlled
  A/B reproduction before declaring root cause.

## 5. Patternicity and Pareidolia (Apophenia)

The evolved human tendency to perceive meaningful patterns in random noise.
* **Trap**: Seeing a "trend" in three flaky CI runs or correlating unrelated
  metric spikes.
* **Countermeasure**: Use statistical baselines, larger sample sizes, and
  randomized property-based tests (PBT) rather than anecdotes.

## 6. Dunning-Kruger Effect

Overestimating competence in unfamiliar domains while underestimating hidden
complexity ("it's just a quick regex / auth wrapper").
* **Trap**: Dismissing concurrency, timezone, or cryptography edge cases as
  trivial.
* **Countermeasure**: Consult domain references, use established libraries,
  and invite adversarial review from domain experts.

## 7. Hindsight Bias

Believing after an incident is resolved that the root cause was "obvious all
along" ("I knew that race condition was there").
* **Trap**: Writing shallow postmortems that blame individuals instead of
  fixing missing guardrails.
* **Countermeasure**: Record hypotheses *before* running experiments; audit
  what signals were genuinely visible at the time.

## 8. Anchoring

Relying too heavily on the first number, stack frame, or user symptom
presented when diagnosing an issue.
* **Trap**: Spending hours optimizing a function mentioned in an initial
  ticket without profiling the whole request path.
* **Countermeasure**: Generate at least three independent hypotheses before
  committing to an investigation path.

## 9. Sunk Cost Fallacy

Continuing to invest in a flawed architecture or patch simply because you
have already spent hours writing it.
* **Trap**: Adding a fifth workaround to a complected class hierarchy instead
  of deleting it and starting fresh.
* **Countermeasure**: Evaluate designs strictly on future simplicity and
  maintenance cost. Use `git checkout` / `git reset` freely to discard dead
  ends.
