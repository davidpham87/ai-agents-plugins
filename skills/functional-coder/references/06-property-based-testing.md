# Property-Based Testing (PBT)

> "Don't write tests that verify what you already thought of. Write tests
> that find what you failed to think of."
> — John Hughes, co-creator of QuickCheck

Unit tests that rely exclusively on hand-crafted examples suffer from severe
confirmation bias. We test the happy path and a few edge cases we already
anticipate (e.g., empty string, zero, null). Property-Based Testing (PBT)
inverts this paradigm by generating hundreds or thousands of synthetic inputs
from generative schemas to rigorously challenge invariants.

---

## 1. Why Property-Based Testing Beats Example Tests

* **Input Coverage**: Example tests check a handful of hardcoded inputs;
  PBT evaluates thousands of generative cases.
* **Edge Cases**: Example tests only cover edge cases the author recalls;
  PBT discovers surprising boundary combinations systematically.
* **Diagnosis**: Example tests produce massive ad-hoc payloads on failure;
  PBT automatically shrinks inputs to minimal reproducible examples.
* **Specification**: Example tests assert concrete values; PBT asserts
  general mathematical and behavioral invariants across the whole domain.

---

## 2. Core Property Patterns

When designing property tests, look for these universal mathematical and
logical invariants:

### A. Round-Trip (Inverses)
Applying an operation followed by its inverse returns the original value:
`decode(encode(x)) == x`
Examples: serialization (JSON, Transit, EDN), parser/printer pairs,
encryption/decryption.

### B. Invariants
Certain characteristics remain strictly true regardless of the input:
* Sorting a collection never changes its length or element multiset.
* Tax calculation never produces a negative amount for positive inputs.
* Validated outputs conform strictly to the declared Malli schema.

### C. Idempotence
Applying an operation multiple times produces the same result as applying
it once:
`f(f(x)) == f(x)`
Examples: database migrations, upserts, text normalization, formatting,
sorting.

### D. Test Oracle (Metamorphic / Reference Comparison)
Compare the output of an optimized or complex algorithm against a simple,
obviously correct (but perhaps slow) reference implementation:
`fast_search(items, query) == naive_linear_search(items, query)`

### E. State Machine (Model-Based Testing)
For stateful systems (e.g., caches, transactional accounts), generate random
sequences of commands (deposit, withdraw, query) and verify that the system
under test behaves identically to a simple in-memory pure map model.

---

## 3. The Power of Shrinking

When a property fails on a massive synthetic input (e.g., a list of 100 items
with deeply nested structures), debugging would be impossible without
**shrinking**.

Modern PBT engines (QuickCheck, `test.check`, `hypothesis`) automatically
search for the minimal reproducing counterexample:
* Truncating strings and vectors.
* Moving numbers closer to zero.
* Removing extraneous dictionary keys.

You receive the smallest possible input that triggers the failure (e.g.,
`items = [0, -1]`).

---

## 4. Practical Implementation: Python with Hypothesis

In Python, the `hypothesis` library provides state-of-the-art PBT:

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sorting_is_idempotent(xs):
    sorted_once = sorted(xs)
    sorted_twice = sorted(sorted_once)
    assert sorted_once == sorted_twice

@given(st.lists(st.integers()))
def test_sorting_preserves_length(xs):
    assert len(sorted(xs)) == len(xs)
```

Strategies can generate composite, domain-specific dictionaries:
```python
user_strategy = st.fixed_dictionaries({
    "user/id": st.uuids().map(str),
    "user/email": st.emails(),
    "user/age": st.integers(min_value=0, max_value=120),
})
```

---

## 5. Practical Implementation: Clojure with Malli & test.check

In Clojure, Malli integrates generative testing directly into schema
definitions:

```clojure
(require '[clojure.test.check.generators :as gen]
         '[clojure.test.check.properties :as prop]
         '[clojure.test.check.clojure-test :refer [defspec]]
         '[malli.core :as m]
         '[malli.generator :as mg])

;; Schema with generative capability
(def Order
  [:map
   [:order/id :uuid]
   [:order/total [:double {:min 0.0 :max 100000.0}]]
   [:order/items [:vector [:string {:min 1}]]]])

;; Generator derived directly from schema
(def order-gen (mg/generator Order))

;; Property test verifying round-trip EDN serialization
(defspec order-roundtrip-edn 100
  (prop/for-all [order order-gen]
    (= order (read-string (pr-str order)))))
```

By deriving generators directly from Malli schemas, you ensure tests always
exercise valid domain data while catching unexpected boundary errors.


---

## 6. REPL-Driven PBT Workflow

In functional development, property verification is not an afterthought
delegated solely to external CI jobs. It is driven continuously from the REPL.

Using `clj-nrepl-eval` or an active nREPL connection:
1. Connect to your running process or subteam nREPL port:
   `clj-nrepl-eval -p <port> "(require '...) (mg/generate Schema)"`
2. Sample data distributions interactively:
   `(mg/sample order-gen 5)`
3. Run single generative properties with small iteration counts (e.g., 10-20
   trials) to receive immediate sub-second feedback:
   `(tc/quick-check 20 my-property)`
4. When a property fails, evaluate the shrunk failure payload directly in the
   REPL to inspect the minimal reproducing case without leaving your editor.

---

## 7. Selective Test Runs and Test Scoping

Running thousands of generative test cases across an entire suite on every
keystroke wastes developer attention and CPU cycles. Adopt a two-phase
execution discipline:

* **Fast Iteration (Targeted Runs)**:
  Target only the specific property or namespace you are modifying:
  - Python: `pytest path/to/test.py::test_specific_property` or `pytest -k name`
  - Clojure: evaluate `(run-property! prop-x 20)` via `clj-nrepl-eval`
* **Final Gate (Full Suite Verification)**:
  Run the complete generative suite with high trial counts (100 to 1,000+
  trials per property) only before committing or merging:
  - Python: `pytest`
  - Clojure: `(run-all-properties!)` or full `lein test` / `clj -M:test`


---

## 8. Consumer and Subscriber Contract PBT

How do you prove that an accretive change will not blow up downstream
consumers or event subscribers? Generative Contract Testing.

Instead of writing a static integration test with one legacy payload:
1. Construct a generator that synthesizes **evolved producer messages**:
   the baseline schema extended with arbitrary additional namespaced keys,
   new optional attributes, and extended metadata.
2. Feed these evolved payloads directly into legacy consumer functions.
3. Assert that the legacy consumer:
   - Successfully extracts its required keys without throwing exceptions.
   - Computes identical outputs regardless of the presence of novel keys.
   - Preserves downstream invariant properties.

By executing this contract test across hundreds of generated permutations, you
mathematically verify that your system's blast radius remains strictly
contained.
