# Schemas a la Carte and Open Systems

> "You don't need a static type system to have rigor, and static type
> systems often complect verification with program evolution."
> — Rich Hickey, *Spec-ulation* (2016)

Two of Rich Hickey's most influential talks, *Spec-ulation* (2016) and
*Maybe Not* (2018), critique the rigid assumptions of static type systems and
propose an alternative architecture for software that evolves over time:
**Schemas a la carte**.

---

## 1. The Trap of Closed Types

Mainstream static typing models information through closed product types
(structs, classes, or records). A closed record specifies:
* Exactly what fields are allowed.
* Exactly what type each field must hold.
* Rejection of any unrecognized attributes.

This complects two distinct questions:
1. "What shape of data do I require *right here, right now* in this function?"
2. "What attributes can exist in this entity throughout the universe?"

When a service adds a new field to its response, a client with closed types
often crashes with a deserialization error. To prevent this, Hickey argues for
**open, extensible information models**:
* Entities are represented as plain associative maps.
* Entities may contain attributes that a particular function does not know
  or care about.
* Functions specify only what they *require* at input and what they *guarantee*
  at output.

---

## 2. Omission over `Maybe` / `Option`

In typed functional programming (Haskell, Scala, Rust), missing data is
commonly represented using the `Option` or `Maybe` monad:
`Option[String]`.

Hickey's *Maybe Not* exposes the flaws in this approach:
* **Complecting presence with type**: `Option[T]` creates a new type wrapper.
  Callers must explicitly wrap (`Some`), unwrap, map, flatMap, or pattern
  match.
* **The Nested Wrapper Absurdity**: What does `Option[Option[T]]` mean? It
  happens frequently in generic code and represents an artifact of the type
  system rather than domain reality.
* **Contextual Optionality**: Is a customer's email address optional? When
  signing up with a phone number, yes. When sending a password reset email,
  no! Email is not an "optional string"; email is a string. The *operation*
  determines whether the attribute is mandatory.

### The Hickey Solution: Omission

In an associative map, optionality is simply **omission**:
```clojure
;; Phone signup: email key is simply not present
{:user/id "+15551234567"}

;; Email signup: email key is present
{:user/id "+15551234567"
 :user/email "ada@example.com"}
```
Do not invent special placeholder values (`nil`, `None`, `null`, `NULL_VALUE`)
when you can simply omit the key. An attribute is either present with a valid
value, or absent.

---

## 3. Validation a la Carte at the Boundaries

Validation should happen at system boundaries (HTTP request ingestion,
message bus consumers, database boundaries), not sprinkled defensively inside
internal pure domain logic.

Clojure provides tools like `clojure.spec` and `Malli` to express schemas
as data:

```clojure
(require '[malli.core :as m])

;; Define attributes independently with universal semantics
(def User
  [:map
   [:user/id :uuid]
   [:user/email [:string {:min 3}]]
   [:user/role {:optional true} [:enum :admin :member :guest]]])

;; Boundary validation
(m/validate User {:user/id #uuid "550e8400-e29b-41d4-a716-446655440000"
                  :user/email "ada@lovelace.org"})
;; => true
```

Benefits of schemas as data:
* **Composable**: Schemas are maps and vectors; you can merge, project,
  or modify them programmatically.
* **A la carte**: A registration endpoint requires `[:user/id :user/email]`;
  a login endpoint requires `[:user/email :user/password]`. The same underlying
  attributes are validated according to the specific context.
* **Accretive Growth**: New optional keys can be added to maps without
  invalidating existing consumers.

---

## 4. Software Evolution: Breaking Changes vs. Accretion

In *Spec-ulation*, Hickey formulated the rules of breaking changes:
* You cannot require more than you did before.
* You cannot provide less than you did before.

If a function accepted `A`, it cannot later require `A` and `B`. That is a
breaking change. If you need new inputs or different behavior, provide a new
function or an accretive, optional attribute.
