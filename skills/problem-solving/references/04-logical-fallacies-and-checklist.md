# Logical Fallacies and Skeptical Engineering Checklist

> "Extraordinary claims require extraordinary evidence."
> — Carl Sagan (core tenet of *The Skeptics' Guide to the Universe*)

Architectural debates and debugging postmortems often derail into informal
logical fallacies. Recognizing these errors keeps technical reasoning sharp
and objective.

---

## 1. Nine Common Logical Fallacies in Engineering

1. **Ad Hominem**: Dismissing a design critique because of who raised it
   (e.g., "a junior wrote that" or "the reviewer just dislikes OOP") instead
   of evaluating the technical argument itself.
2. **False Authority (Appeal to Authority)**: Accepting an unverified claim
   solely because a senior architect, vendor, or famous blog endorsed it,
   without checking evidence in *your* system.
3. **Straw Man**: Misrepresenting a simpler proposal ("so you want zero
   types and no validation anywhere?") to make it easy to attack.
4. **False Dilemma (False Dichotomy)**: Presenting two extreme options as
   the only choices ("either we build a rigid class hierarchy or we have
   unmaintainable spaghetti") while ignoring open schemas and pure functions.
5. **Slippery Slope**: Claiming an incremental, bounded change will
   inevitably trigger catastrophe without demonstrating a causal mechanism.
6. **Ad Populum (Bandwagon)**: Assuming a framework or pattern is optimal
   solely because "everyone in the industry uses it."
7. **Tu Quoque ("You Too")**: Deflecting a valid bug or complexity critique
   by pointing out flaws in another module ("your service has tech debt too").
8. **Special Pleading**: Exempting your favorite module from rules applied
   everywhere else ("the 20-line limit shouldn't apply to *my* parser").
9. **Circular Reasoning (Begging the Question)**: Using the conclusion as its
   own premise ("this cache is thread-safe because it's our safe cache").

---

## 2. Core Principles of Scientific Reasoning

* **Falsifiability**: A debugging hypothesis or performance claim is useless
  unless you can state an experiment that would *prove it false*.
* **Occam's Razor (Parsimony)**: Among competing explanations that fit all
  observed facts, prefer the one requiring the fewest unproven assumptions
  (e.g., a stale local config before a cosmic compiler bug).
* **Burden of Proof**: Whoever proposes adding complexity (a new service,
  cache, or abstraction) bears the burden of proving measurable necessity.

---

## 3. Practical Skeptical Engineering Checklist

Run this audit before finalizing any non-trivial fix or design:

- [ ] **Primary Evidence**: Did I inspect the actual logs, code, and test
      outputs rather than relying on memory or second-hand summaries?
- [ ] **Polya Clarity**: Can I state the unknown, data, and condition in
      plain terms without framework jargon?
- [ ] **Multiple Hypotheses**: Did I compare at least two competing designs
      or root-cause theories before committing?
- [ ] **Falsification Test**: What specific test or measurement *disproves*
      my diagnosis if I am wrong?
- [ ] **Parsimony Check**: Does this solution introduce the fewest possible
      new assumptions, places, or coupled dependencies?
- [ ] **Bias Audit**: Am I defending this code due to **Sunk Cost**,
      **Confirmation Bias**, or **Anchoring**?
- [ ] **Look Back**: Did I verify invariants with independent checks (e.g.,
      PBT) and record what can be generalized?
