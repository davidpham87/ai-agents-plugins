---
name: problem-solving
description: >-
  Structured problem solving and skeptical critical thinking combining George
  Polya's How to Solve It (4 steps and heuristics) with Dr. Steven Novella's
  Skeptics' Guide to the Universe (cognitive biases, logical fallacies, and
  scientific skepticism) for software engineering, debugging, and design.
---

# Problem Solving and Skeptical Auditing

Effective engineering requires two complementary disciplines:
1. **Constructive Synthesis (George Polya)**: Systematic heuristics to
   understand unfamiliar problems, devise plans, and generalize solutions.
2. **Skeptical Auditing (Dr. Steven Novella)**: Rigorous cognitive hygiene to
   prevent human biases, patternicity, and logical fallacies from corrupting
   diagnosis or architecture.

## Integrated Workflow

Pair Polya's four phases with Novella's skeptical checkpoints at every step:

1. **Understand the Problem**
   *Polya*: Identify the unknown, the data, and the conditions. Draw a figure
   or introduce clear notation.
   *Skeptic*: Check for **Anchoring** and **Confirmation Bias**; verify raw
   observations before accepting a bug report's framing.
2. **Devise a Plan**
   *Polya*: Apply heuristics (working backwards, auxiliary problem,
   specialization, generalization, analogy).
   *Skeptic*: Apply **Occam's Razor** and **Falsifiability**; reject untestable
   root-cause theories and guard against **Sunk Cost** attachment.
3. **Carry Out the Plan**
   *Polya*: Verify each step independently; prove correctness or run targeted
   checks.
   *Skeptic*: Guard against **Post Hoc** illusions and **Patternicity** when
   interpreting logs or flaky test results.
4. **Look Back**
   *Polya*: Examine the solution, check invariants, and ask whether the method
   can be generalized to other problems.
   *Skeptic*: Counter **Hindsight Bias**; document what you actually knew
   versus what you only rationalized after seeing the fix.

## Progressive Discovery & References

- [Polya's Four Steps][ref-01]
  Understand, Plan, Execute, and Look Back adapted for software systems.
- [Polya's Heuristics Toolbox][ref-02]
  Working backwards, Inventor's Paradox, invariants, and decomposition.
- [Skeptical Cognitive Biases][ref-03]
  Novella's SGU taxonomy of neuropsychological traps and countermeasures.
- [Logical Fallacies & Checklist][ref-04]
  Fallacies, falsifiability, Occam's Razor, and an engineering checklist.

[ref-01]: references/01-polya-four-steps.md
[ref-02]: references/02-polya-heuristics-toolbox.md
[ref-03]: references/03-skeptical-cognitive-biases.md
[ref-04]: references/04-logical-fallacies-and-checklist.md
