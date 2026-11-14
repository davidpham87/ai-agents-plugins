---
name: problem-solving
description: >-
  Structured problem solving and skeptical critical thinking combining George
  Polya's How to Solve It (4 steps, 10 heuristics), practical engineering and
  design techniques, systematic diagnostic tactics, and Dr. Steven Novella's
  Skeptics' Guide to the Universe (biases, fallacies, scientific skepticism).
---

# Problem Solving and Skeptical Auditing

Effective engineering integrates three complementary disciplines:
1. **Constructive Synthesis (Polya & Practical Techniques)**: Systematic
   heuristics, first-principles framing, pre-mortems, bottleneck analysis,
   time-boxed spikes, and cost-of-delay triage.
2. **Diagnostic & Debugging Tactics**: Search-space halving (`git bisect`,
   Wolf Fence), minimal repros, differential diagnosis, timeline alignment,
   and controlled one-variable experiments.
3. **Skeptical Auditing (Dr. Steven Novella)**: Rigorous cognitive hygiene to
   prevent biases, patternicity, and logical fallacies from corrupting design
   or root-cause analysis.

## Integrated Workflow

Pair Polya's four phases with practical tactics and skeptical checkpoints:

1. **Understand the Problem**
   *Polya*: Define the unknown, data, I/O contract, hard bounds, and
   non-goals; draw a figure and ground with tiny concrete cases.
   *Tactics*: Shrink noise with **Feynman Teach-Back**, **MRE / Delta
   Debugging**, **Differential Diagnosis**, or **Timeline Reconstruction**.
   *Skeptic*: Check **Anchoring** and **Confirmation Bias**; verify raw
   artifacts before accepting a bug report's framing.
2. **Devise a Plan**
   *Polya*: Apply heuristics (working backwards, wishful thinking, auxiliary
   scaffolding, representation shift, abstraction ladder, invariants).
   *Practical*: Use **First Principles**, **Morphological Matrix**,
   **Pre-Mortem Inversion**, **Theory of Constraints**, **Spikes**, and
   **Cost-of-Delay Triage**; compare >= 2 plans on risk and reversibility.
   *Skeptic*: Apply **Occam's Razor** and **Falsifiability**; reject untestable
   root-cause theories and guard against **Sunk Cost** attachment.
3. **Carry Out the Plan**
   *Polya*: Work in verifiable checkpoints with intermediate invariant guards
   and explicit stall/pivot triggers; test each step in isolation.
   *Tactics*: Isolate faults via **`git bisect`**, **Wolf Fence** probes, and
   **Controlled One-Variable Experiments** (predict -> falsify).
   *Skeptic*: Guard against **Post Hoc** illusions and **Patternicity** when
   interpreting logs, metrics, or flaky test results.
4. **Look Back**
   *Polya*: Verify with an independent oracle, simplify/delete dead code,
   generalize across sibling modules, and add permanent regression guards.
   *Tactics*: Run **Branching 5 Whys** on incidents to break multiple causal
   paths rather than forcing a single linear story.
   *Skeptic*: Counter **Hindsight Bias**; document what primary evidence proved
   and which false leads were eliminated.

## Progressive Discovery & References

- [Polya's Four Steps][ref-01]
  Four-phase loop with I/O contracts, plan criteria, checkpoints, and guards.
- [Polya's Heuristics Toolbox][ref-02]
  Quick-selector and 10 heuristics: working backwards, relaxation, invariants.
- [Skeptical Cognitive Biases][ref-03]
  Novella's SGU taxonomy of neuropsychological traps and countermeasures.
- [Logical Fallacies & Checklist][ref-04]
  Fallacies, falsifiability, Occam's Razor, and an engineering checklist.
- [Practical Problem-Solving Techniques][ref-05]
  First principles, pre-mortem, bottlenecks, spikes, Feynman, triage matrix.
- [Practical Diagnostic & Debugging Tactics][ref-06]
  Bisection, Wolf Fence, MRE, diff diagnosis, timelines, branching 5 Whys.

[ref-01]: references/01-polya-four-steps.md
[ref-02]: references/02-polya-heuristics-toolbox.md
[ref-03]: references/03-skeptical-cognitive-biases.md
[ref-04]: references/04-logical-fallacies-and-checklist.md
[ref-05]: references/05-practical-solving-techniques.md
[ref-06]: references/06-diagnostic-tactics.md
