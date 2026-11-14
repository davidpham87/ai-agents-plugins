"""Property-Based Testing (PBT) in Python using Hypothesis.

Demonstrates Rich Hickey's design philosophy in Python:
- Plain immutable data structures (dicts, tuples, numbers, strings)
- Pure functions with no hidden mutations or side effects
- Namespaced keys representing universal information models
- PBT invariants, round-trips, idempotence, and model/oracle checks
"""

from __future__ import annotations
import json
import math
from typing import Any, Mapping, Sequence
from cytoolz import assoc, merge, pipe, reduce as creduce
from cytoolz.curried import filter as cfilter, map as cmap
from hypothesis import given, strategies as st


# --- Pure Domain Functions ---

_BRAID_KEYS = (
    "braid/state-time",
    "braid/data-code",
    "braid/io-logic",
    "braid/policy-mechanism",
    "braid/global-coupling",
)


def compute_simplicity_score(arch_flags: Mapping[str, bool]) -> int:
    """Rich Hickey Simplicity Score (0-100) via cytoolz pipeline."""
    deductions = pipe(
        _BRAID_KEYS,
        cfilter(lambda key: bool(arch_flags.get(key, False))),
        cmap(lambda _key: 20),
        sum,
    )
    return max(0, 100 - deductions)


def normalize_text(text: str) -> str:
    """Idempotent whitespace and case normalizer."""
    return " ".join(text.strip().lower().split())


def calculate_line_item(item: Mapping[str, Any]) -> float:
    """Calculate line item cost from plain mapping."""
    price = float(item.get("item/price", 0.0))
    qty = int(item.get("item/qty", 0))
    return round(price * qty, 2)


def calculate_subtotal(items: Sequence[Mapping[str, Any]]) -> float:
    """Pure cytoolz pipeline reduction over line items."""
    return round(pipe(items, cmap(calculate_line_item), sum), 2)


def apply_discount(subtotal: float, discount_code: str | None) -> float:
    """A la carte discount rules without mutation."""
    base = round(subtotal, 2)
    if base <= 0.0 or not discount_code:
        return base
    code = discount_code.strip().upper()
    if code == "SAVE10":
        return round(base * 0.90, 2)
    if code == "HALF":
        return round(base * 0.50, 2)
    return base


def calculate_tax(amount: float, region: str) -> float:
    """Pure tax calculation based on regional code."""
    rates = {
        "EU": 0.20,
        "UK": 0.20,
        "US-CA": 0.09,
        "US-NY": 0.08,
    }
    rate = rates.get(region.upper(), 0.05)
    return round(amount * rate, 2)


def legacy_order_subscriber(order: Mapping[str, Any]) -> dict[str, Any]:
    """Legacy consumer extracting only the attributes it requires."""
    order_id = str(order["order/id"])
    items = order.get("order/items", [])
    subtotal = calculate_subtotal(items)
    return {
        "subscriber/order-id": order_id,
        "subscriber/item-count": len(items),
        "subscriber/subtotal": subtotal,
    }


def serialize_order(order: Mapping[str, Any]) -> str:
    """Serialize order map to deterministic JSON string."""
    return json.dumps(order, sort_keys=True, separators=(",", ":"))


def deserialize_order(payload: str) -> dict[str, Any]:
    """Deserialize JSON string into plain dictionary."""
    return json.loads(payload)


# --- Hypothesis Strategies (Generators) ---

item_strategy = st.fixed_dictionaries(
    {
        "item/id": st.uuids().map(str),
        "item/name": st.text(
            alphabet=st.characters(categories=["L", "N", "Zs"]),
            min_size=1,
            max_size=30,
        ),
        "item/price": st.floats(
            min_value=0.01,
            max_value=1000.0,
            allow_nan=False,
            allow_infinity=False,
        ).map(lambda p: round(p, 2)),
        "item/qty": st.integers(min_value=1, max_value=50),
    }
)

order_strategy = st.fixed_dictionaries(
    {
        "order/id": st.uuids().map(str),
        "order/region": st.sampled_from(
            ["EU", "UK", "US-CA", "US-NY", "OTHER"]
        ),
        "order/items": st.lists(item_strategy, min_size=0, max_size=10),
    }
)


accretive_metadata_strategy = st.dictionaries(
    keys=st.sampled_from(
        [
            "order/loyalty-points",
            "order/delivery-notes",
            "order/tracking-code",
            "campaign/promo-id",
            "payment/provider-reference",
        ]
    ),
    values=st.text(min_size=1, max_size=40) | st.integers(0, 1000),
    max_size=5,
)


simplicity_flags_strategy = st.fixed_dictionaries(
    {
        "braid/state-time": st.booleans(),
        "braid/data-code": st.booleans(),
        "braid/io-logic": st.booleans(),
        "braid/policy-mechanism": st.booleans(),
        "braid/global-coupling": st.booleans(),
    }
)


# --- Property Tests ---

@given(order_strategy)
def test_order_roundtrip_json_serialization(order: dict[str, Any]) -> None:
    """Property: Round-trip encode/decode restores exact value."""
    payload = serialize_order(order)
    reconstituted = deserialize_order(payload)
    assert reconstituted == order


@given(st.text())
def test_text_normalization_is_idempotent(text: str) -> None:
    """Property: Normalization is idempotent: f(f(x)) == f(x)."""
    normalized_once = normalize_text(text)
    normalized_twice = normalize_text(normalized_once)
    assert normalized_once == normalized_twice


@given(
    st.floats(min_value=0.0, max_value=1e6, allow_nan=False),
    st.sampled_from([None, "", "SAVE10", "HALF", "UNKNOWN"]),
)
def test_discount_invariant(amount: float, code: str | None) -> None:
    """Property: Discounted amount never exceeds original subtotal."""
    discounted = apply_discount(amount, code)
    assert 0.0 <= discounted <= round(amount, 2)


@given(st.lists(item_strategy, min_size=1, max_size=20))
def test_oracle_subtotal_matches_manual_sum(
    items: list[dict[str, Any]],
) -> None:
    """Property: Metamorphic check against cytoolz.reduce oracle."""
    reference_sum = round(
        creduce(
            lambda acc, it: acc
            + round(float(it["item/price"]) * int(it["item/qty"]), 2),
            items,
            0.0,
        ),
        2,
    )
    assert math.isclose(
        calculate_subtotal(items),
        reference_sum,
        abs_tol=0.02,
    )


@given(order_strategy, accretive_metadata_strategy)
def test_consumer_contract_non_breaking_evolution(
    order: dict[str, Any],
    extra_fields: dict[str, Any],
) -> None:
    """Property: Accretive producer changes do not break legacy consumers."""
    baseline_result = legacy_order_subscriber(order)
    evolved_order = merge(order, extra_fields)
    evolved_result = legacy_order_subscriber(evolved_order)
    assert evolved_result == baseline_result


@given(simplicity_flags_strategy)
def test_simplicity_score_invariants(flags: dict[str, bool]) -> None:
    """Property: Simplicity score invariants (bounds, monotonicity)."""
    score = compute_simplicity_score(flags)
    assert 0 <= score <= 100
    assert score % 20 == 0
    braided = assoc(flags, "braid/state-time", True)
    assert compute_simplicity_score(braided) <= score


if __name__ == "__main__":
    print("Running Hypothesis property tests...")
    test_order_roundtrip_json_serialization()
    test_text_normalization_is_idempotent()
    test_discount_invariant()
    test_oracle_subtotal_matches_manual_sum()
    test_consumer_contract_non_breaking_evolution()
    test_simplicity_score_invariants()
    print("All Python property-based tests passed successfully!")
