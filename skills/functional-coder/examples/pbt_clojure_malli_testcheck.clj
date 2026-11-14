(ns functional-coder.examples.pbt-clojure-malli-testcheck
  "Demonstrates Rich Hickey's Clojure design philosophy:
   - Plain namespaced maps without custom record types
   - Open polymorphism via multimethods
   - Schemas a la carte with Malli
   - Generative Property-Based Testing (PBT) with test.check
   - REPL-driven interactive property evaluation and selective test runs."
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is run-tests testing]]
            [clojure.test.check :as tc]
            [clojure.test.check.clojure-test :refer [defspec]]
            [clojure.test.check.generators :as gen]
            [clojure.test.check.properties :as prop]
            [malli.core :as m]
            [malli.generator :as mg]))

;; --- Domain Logic: Pure Functions & Open Multimethods ---

(defmulti calculate-tax
  "Open polymorphic tax calculation dispatching on :order/region."
  :order/region)

(defmethod calculate-tax :region/eu [_order amount]
  (double (* amount 0.20)))

(defmethod calculate-tax :region/uk [_order amount]
  (double (* amount 0.20)))

(defmethod calculate-tax :region/us [_order amount]
  (double (* amount 0.08)))

(defmethod calculate-tax :default [_order amount]
  (double (* amount 0.05)))

(defn line-item-total
  "Pure calculation of line item price * quantity."
  [item]
  (double (* (:item/price item) (:item/qty item))))

(defn calculate-subtotal
  "Pure functional reduction over order items."
  [order]
  (double (reduce + 0.0 (map line-item-total (:order/items order)))))

(defn calculate-order-total
  "Composes subtotal and polymorphic tax calculation."
  [order]
  (let [subtotal (calculate-subtotal order)
        tax (calculate-tax order subtotal)]
    {:order/id (:order/id order)
     :order/subtotal subtotal
     :order/tax tax
     :order/total (+ subtotal tax)}))

;; --- Schemas a la Carte with Malli ---

(def ItemSchema
  [:map
   [:item/id :uuid]
   [:item/name [:string {:min 1 :max 40}]]
   [:item/price [:double {:min 0.01 :max 5000.0}]]
   [:item/qty [:int {:min 1 :max 100}]]])

(def OrderSchema
  [:map
   [:order/id :uuid]
   [:order/region [:enum :region/eu :region/uk :region/us :region/row]]
   [:order/items [:vector {:min 0 :max 10} ItemSchema]]])

;; Generators derived directly from Malli schemas
(def order-gen
  (mg/generator OrderSchema))

;; --- Property-Based Testing Properties ---

;; Property 1: Round-trip EDN serialization
(def prop-roundtrip-edn
  (prop/for-all [order order-gen]
    (= order (edn/read-string (pr-str order)))))

;; Property 2: Invariant: Subtotal is always non-negative
(def prop-subtotal-non-negative
  (prop/for-all [order order-gen]
    (let [subtotal (calculate-subtotal order)]
      (>= subtotal 0.0))))

;; Property 3: Metamorphic / Oracle check: subtotal matches sum of line items
(def prop-oracle-subtotal
  (prop/for-all [order order-gen]
    (let [items (:order/items order)
          expected (double (reduce (fn [acc it]
                                     (+ acc (* (:item/price it)
                                               (:item/qty it))))
                                   0.0
                                   items))
          actual (calculate-subtotal order)]
      (< (Math/abs (- actual expected)) 0.001))))

;; Property 4: Invariant: Total is greater than or equal to subtotal
(def prop-total-exceeds-subtotal
  (prop/for-all [order order-gen]
    (let [summary (calculate-order-total order)]
      (>= (:order/total summary) (:order/subtotal summary)))))

;; --- defspec declarations for Clojure Test Suite Integration ---

(defspec check-roundtrip-edn 50 prop-roundtrip-edn)
(defspec check-subtotal-non-negative 50 prop-subtotal-non-negative)
(defspec check-oracle-subtotal 50 prop-oracle-subtotal)
(defspec check-total-exceeds-subtotal 50 prop-total-exceeds-subtotal)

;; --- REPL-Driven & Selective Test Helpers ---

(defn run-property!
  "Evaluates a single property interactively at the REPL (selective run)."
  [property num-tests]
  (let [result (tc/quick-check num-tests property)]
    (println "Property result:"
             (select-keys result [:result :num-tests :pass?]))
    (:pass? result)))

(defn run-all-properties!
  "Runs all property checks in this namespace (full suite gate)."
  []
  (println "Running full PBT suite (Clojure + Malli + test.check)...")
  (let [props [["Round-trip EDN" prop-roundtrip-edn]
               ["Subtotal non-negative" prop-subtotal-non-negative]
               ["Oracle subtotal" prop-oracle-subtotal]
               ["Total >= subtotal" prop-total-exceeds-subtotal]]
        results (mapv (fn [[name-str p]]
                        (let [res (tc/quick-check 50 p)]
                          (println (format "  * %s: %s (%d tests)"
                                           name-str
                                           (if (:pass? res) "PASS" "FAIL")
                                           (:num-tests res)))
                          (:pass? res)))
                      props)]
    (every? true? results)))

(defn -main
  "Command-line entry point for running property checks."
  [& _args]
  (let [all-passed? (run-all-properties!)]
    (if all-passed?
      (println "All Clojure PBT properties passed!")
      (throw (ex-info "Some Clojure PBT properties failed!" {})))))

(when (= *file* (System/getProperty "babashka.file"))
  (-main))
