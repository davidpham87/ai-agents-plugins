# Naming and Semantic Precision

> "Names are the primary way we convey intention and meaning in software.
> When names are vague or lazy, systems decompose into cognitive mud."
> — Rich Hickey, *Design in Practice*

Rich Hickey emphasizes that software engineering is an exercise in applied
semantics. Code does not merely instruct the CPU; it models facts and
relationships in human domains. Sloppy naming complects intent with
incidental implementation details.

---

## 1. Etymology and Dictionary Grounding

When designing an API, do not guess what a word might mean, and do not invent
internal engineering jargon. Look up the dictionary definition and etymology:

* **Verify the root**: Does the word accurately describe the operational
  contract? For example, *transduce* means "to lead across or transform from
  one form to another", which precisely describes reducing transformations
  independent of context.
* **Avoid vacant suffixes**: Words like `Manager`, `Processor`, `Handler`,
  `Helper`, `Controller`, or `Util` convey almost zero semantic content. They
  signal that the author did not take the time to decompose what the component
  actually *does*.
* **Prefer specific domain actions**: Replace `UserManager.process(data)` with
  pure functions such as `authenticate`, `enroll`, `deprecate-token`, or
  `reconcile-billing`.

---

## 2. Qualified Keywords: Universal Semantics

In conventional OOP and untyped dictionaries, attributes are identified by
unqualified, local strings or keys:

```json
{
  "id": 101,
  "name": "Widget A",
  "status": "active"
}
```

What does `"id"` mean? Is it a database primary key? A UUID? An SKU?
If you merge this dictionary with a user record that also has an `"id"`,
one key will clobber the other.

Clojure solves this through **namespaced keywords** (qualified identifiers):

```clojure
{:order/id           "ord-9871"
 :order/status       :order.status/pending
 :user/id            "usr-3341"
 :customer/tier      :customer.tier/gold
 :inventory.sku/code "SKU-992-BLU"}
```

Why qualified keys matter:
1. **Global Uniqueness**: An `:order/id` is semantically distinct from a
   `:user/id` or `:transaction/id`.
2. **Safe Merging**: You can merge multiple maps into an aggregate view without
   naming collisions or artificial nesting.
3. **Information Model as a Graph**: Attributes exist independently of
   container classes. They resemble RDF predicates or relational database
   columns, allowing data to flow seamlessly across microservices and storage
   engines.
4. **Autonomous Semantics**: You do not need to look at enclosing class
   definitions or schemas to understand what `:order/amount` represents.

---

## 3. Pure Naming Conventions

Follow these functional guidelines when naming components:

* **Predicates**: Suffix with `?` (Clojure) or prefix `is_`/`has_`.
  Example: `valid-user?` or `empty?` rather than `validUser()`.
* **Transformations**: Express source-to-target with `->`.
  Example: `order->invoice` rather than `ConvertOrderData`.
* **Pure Actions**: Use concise, active verbs.
  Example: `parse-edn` or `calculate-tax` rather than `DataHandler`.
* **Side Effects**: Suffix mutating or I/O operations with `!`.
  Example: `save-customer!` rather than `saveCustomer`.
* **Collections**: Use simple plural nouns.
  Example: `users` or `active-ids` rather than `UserListObject`.

Names should be accurate, concise, and devoid of implementation baggage.
When you choose names grounded in clear semantic definitions, your codebase
remains comprehensible for years to come.
