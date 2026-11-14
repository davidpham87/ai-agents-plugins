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
from hypothesis import given, strategies as st


# --- Pure Domain Functions ---

def normalize_text(text: str) -> str:
    """Idempotent whitespace and case normalizer."""
    return " ".join(text.strip().lower().split())


def calculate_line_item(item: Mapping[str, Any]) -> float:
    """Calculate line item cost from plain mapping."""
    price = float(item.get("item/price", 0.0))
    qty = int(item.get("item/qty", 0))
    return round(price * qty, 2)


def calculate_subtotal(items: Sequence[Mapping[str, Any]]) -> float:
    """Pure reduction over line items."""
    return round(sum(calculate_line_item(item) for item in items), 2)


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
    """Property: Metamorphic check against reference loop implementation."""
    reference_sum = 0.0
    for it in items:
        reference_sum += round(float(it["item/price"]) * int(it["item/qty"]), 2)
    reference_sum = round(reference_sum, 2)

    assert math.isclose(
        calculate_subtotal(items),
        reference_sum,
        abs_tol=0.02,
    )


if __name__ == "__main__":
    print("Running Hypothesis property tests...")
    test_order_roundtrip_json_serialization()
    test_text_normalization_is_idempotent()
    test_discount_invariant()
    test_oracle_subtotal_matches_manual_sum()
    print("All Python property-based tests passed successfully!")
