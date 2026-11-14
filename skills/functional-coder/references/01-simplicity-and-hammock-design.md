# Simplicity and Hammock-Driven Design

> "Simplicity is a prerequisite for reliability."
> — Edsger W. Dijkstra

In the software industry, "easy" is constantly confused with "simple".
Rich Hickey's talks *Simple Made Easy* (2011) and *Hammock-Driven Development*
(2010) reoriented modern functional software engineering around the
fundamental distinction between these concepts.

---

## 1. Simple vs. Easy

The word roots reveal the profound distinction:

* **Simple** comes from Latin *simplex*: "one fold", single, unbraided,
  uncompounded. A simple component has one role, one concept, one task.
  Simplicity is an **objective, architectural property**.
* **Easy** comes from Old French *aisié* (at ease) and Latin *adjacens* (lying
  near). It means "near at hand", familiar, comfortable, or requiring little
  immediate physical or mental exertion. Ease is a **subjective, relative
  experience**.

```
Simple (Objective)                Easy (Subjective)
--------------------------------  --------------------------------
Unbraided, single concern         Familiar to your background
Focuses on constructs/concepts    Near to your keyboard / IDE
Independent of observer           Depends on what you already know
Maintains velocity over time      Fast at minute 5; painful at year 2
```

When developers reach for tools because they are "easy" (e.g., ORMs, monkey
patching, stateful singletons, magic decorators), they frequently intertwine
distinct concerns. This creates systemic debt that no amount of refactoring
can comfortably undo.

---

## 2. Complecting vs. Decomplecting

To **complect** (*plectere*: to braid or twist together) means to interweave
two or more separate concepts into an indivisible whole.

Examples of complected concerns in conventional development:
* **State and Time**: In imperative languages, variables overwrite memory
  locations. You cannot see past values; time and value are smashed together.
* **Syntax and Data Structure**: Rigid object hierarchies bind serialization,
  memory layout, and behavioral methods into a single class definition.
* **Identity and Value**: An object reference points to a mutable memory
  container, blurring the distinction between what something *is* right now
  and what it is called over its lifetime.
* **Computation and Coordination**: Function execution mixed with threading,
  locking, or async queue polling.

To **decomplect** is the engineer's primary duty:
1. Untangle what can be separate.
2. Provide pure, composable primitives.
3. Combine them explicitly at the edges only when strictly necessary.

---

## 3. Hammock-Driven Development

Programmers suffer from an occupational hazard: the compulsion to type.
When faced with a requirement or a bug, our instinct is to sit at the keyboard,
open an editor, and start banging out code or running unit tests.

Hickey identifies two distinct classes of software defects:
1. **Typing Defects**: Syntax errors, typos, null pointers, off-by-one errors.
   These are cheap, immediately detectable, and handled easily by compilers,
   linters, or basic tests.
2. **Design Defects**: Complected state, incorrect abstractions, wrong
   problem formulation. These are catastrophic, expensive, and cannot be
   fixed by typing faster.

### The Hammock Protocol

The hammock is not a metaphor for laziness; it is an instrument of intense,
focused cognition.

1. **State the Problem Explicitly**:
   Write down what you are trying to solve in plain natural language. If you
   cannot describe the problem without referencing code artifacts, you do not
   yet understand the problem.
2. **Gather Facts and Identify Constraints**:
   Distinguish between hard requirements (facts) and assumptions (conveniences).
3. **Generate Multiple Alternative Designs**:
   Never settle on the first workable idea. First ideas are invariably
   borrowed or reflexive. Compare at least two or three radically different
   architectures.
4. **Step Away from the Keyboard**:
   The human brain has two processing engines: the conscious, focus-driven
   mind (good for immediate logic) and the background subconscious mind (good
   for pattern matching, association, and synthesis).
   Take a walk. Lie down. Sleep on it. The background mind works while you
   are disconnected.
5. **Wake and Scrutinize**:
   Re-evaluate candidates against simplicity metrics. Does any component
   touch more than one concern? If so, decomplect it before writing a single
   line of implementation code.
