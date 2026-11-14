# Polymorphism and Open Extension

Polymorphism is commonly conflated with object-oriented class inheritance.
In traditional OOP, dispatch is tied to single-class inheritance hierarchies,
encapsulated methods, and the runtime `vtable`.

Rich Hickey decoupled polymorphism from classes, providing two distinct
and open mechanisms in Clojure:
1. **Multimethods**: Arbitrary dispatch on any computation or hierarchy.
2. **Protocols**: Fast, type-based dispatch that solves the Expression Problem.

---

## 1. Multimethods: Decoupling Dispatch from Types

In standard OOP, a method call `obj.calculate()` dispatches solely on the
class of `obj` (single dispatch).

Clojure's multimethods separate the **dispatch decision** from the **execution
logic**. You supply an arbitrary pure function to determine the dispatch
value:

```clojure
(defmulti calculate-tax
  "Calculates sales tax based on region and customer category."
  (fn [order] [(:order/region order) (:customer/tier order)]))

(defmethod calculate-tax [:eu :consumer] [order]
  (* (:order/amount order) 0.20))

(defmethod calculate-tax [:eu :business] [order]
  0.0) ;; Reverse charge VAT

(defmethod calculate-tax :default [order]
  (* (:order/amount order) 0.05))
```

Key architectural benefits:
* **Multiple Dispatch**: Dispatch on combinations of arguments, values, or
  attributes, not just the type of argument 0.
* **Open Extension**: Consumers of your library can define new `defmethod`
  implementations for their own custom tags without modifying your source.
* **No Class Hierarchy Required**: Plain maps containing plain data drive the
  behavior.

### Ad-hoc Hierarchies with `derive`

Multimethods do not require inheritance, but they support open taxonomy
through Clojure's global or local hierarchies:

```clojure
(derive :tax/vat-standard :tax/vat)
(derive :tax/vat-reduced  :tax/vat)

(isa? :tax/vat-standard :tax/vat) ;; => true
```

Hierarchies are open sets of relationships between keywords or symbols,
completely independent of any data layout or memory structure.

---

## 2. Protocols: Solving the Expression Problem

The **Expression Problem** is a classic software challenge:
* Can you add new data types to existing operations without touching the
  existing code?
* Can you add new operations to existing data types without touching the
  existing code?
* Can you do both safely and without recompilation or monkey-patching?

OOP makes adding new types easy (new subclass), but adding new operations
requires modifying the base class or introducing complex Visitor patterns.
Functional programming makes adding new operations easy (new function with
pattern matching), but adding new data variants requires editing existing
functions.

Clojure protocols (`defprotocol`) solve both axes:

```clojure
(defprotocol Renderable
  (render [this format] "Render the entity into the target format."))

;; Extend existing core type to our protocol without altering Java or Clojure
;; source definitions.
(extend-protocol Renderable
  java.lang.String
  (render [this format]
    (case format
      :html (str "<span>" this "</span>")
      :text this))

  clojure.lang.PersistentHashMap
  (render [this format]
    (case format
      :json (pr-str this)
      :edn  (pr-str this))))
```

Protocols provide:
* Interface-like high-performance polymorphic dispatch (JVM interface speed).
* The ability to extend types you did not write (e.g., `java.lang.String`,
  built-in maps) to protocols you just authored.
* The ability to extend your types to protocols authored by third parties.

---

## 3. Decomplecting Inheritance

Class inheritance complects at least four separate concerns:
1. **Data layout**: What fields exist in memory.
2. **Behavioral implementation**: Default code for methods.
3. **Type taxonomy**: Subtyping relationship (`is-a`).
4. **Namespace grouping**: Which methods belong together.

Rich Hickey's advice: never use class inheritance for code reuse. Favor plain
maps for data layout, pure functions for reuse, and protocols or multimethods
for open polymorphic extension.
