from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime

import pytest

from shop_data.generator import generate
from tests.conftest import EARLY, LOADED_AT, SMALL, rows

TIMESTAMP_COLUMNS = {
    "customers": ["signup_at", "updated_at"],
    "products": ["created_at", "updated_at"],
    "orders": ["placed_at", "shipped_at", "delivered_at", "cancelled_at", "returned_at"],
    "payments": ["created_at"],
    "web_events": ["occurred_at"],
}


def test_same_seed_same_data(late):
    again = generate(SMALL, loaded_at=LOADED_AT)
    assert again.tables == late.tables


def test_different_seed_different_data(late):
    other = generate(replace(SMALL, seed=8), loaded_at=LOADED_AT)
    assert other.tables["orders"] != late.tables["orders"]


def test_load_time_only_changes_the_load_column(late):
    reloaded = generate(SMALL, loaded_at=datetime(2030, 1, 1))
    for name, columns in late.tables.items():
        for column, values in columns.items():
            if column != "_loaded_at":
                assert reloaded.tables[name][column] == values, (name, column)


def test_nothing_after_as_of_is_visible(early):
    for table, columns in TIMESTAMP_COLUMNS.items():
        for column in columns:
            stamps = [v for v in early.tables[table][column] if v is not None]
            assert stamps and max(stamps) <= EARLY, (table, column)


def test_early_load_is_a_consistent_prefix_of_the_late_one(early, late):
    late_orders = {r["order_id"]: r for r in rows(late, "orders")}
    early_orders = rows(early, "orders")
    assert 0 < len(early_orders) < len(late_orders)
    progressed = 0
    for order in early_orders:
        later = late_orders[order["order_id"]]
        assert (order["customer_id"], order["placed_at"]) == (
            later["customer_id"],
            later["placed_at"],
        )
        progressed += order["status"].lower() != later["status"].lower()
    assert progressed > 0  # some orders shipped / were delivered / returned in between


def test_customer_changes_between_loads_move_updated_at(early, late):
    early_customers = {r["customer_id"]: r for r in rows(early, "customers")}
    changed = 0
    for customer in rows(late, "customers"):
        before = early_customers.get(customer["customer_id"])
        if before is None:
            continue
        tracked = ("email", "country_code", "loyalty_tier")
        if any(before[k] != customer[k] for k in tracked):
            changed += 1
            assert EARLY < customer["updated_at"] <= SMALL.end
        else:
            assert before["updated_at"] == customer["updated_at"]
    assert changed > 0


def test_referential_integrity(late):
    customers = set(late.tables["customers"]["customer_id"])
    products = set(late.tables["products"]["product_id"])
    orders = set(late.tables["orders"]["order_id"])
    assert set(late.tables["orders"]["customer_id"]) <= customers
    assert set(late.tables["order_items"]["order_id"]) == orders  # every order has lines
    assert set(late.tables["order_items"]["product_id"]) <= products
    assert set(late.tables["payments"]["order_id"]) == orders  # every order was paid
    event_orders = {o for o in late.tables["web_events"]["order_id"] if o is not None}
    assert event_orders == orders


@pytest.mark.parametrize("as_of_fixture", ["early", "late"])
def test_payments_reconcile_in_raw(request, as_of_fixture):
    raw = request.getfixturevalue(as_of_fixture)
    owed = defaultdict(int)
    for item in rows(raw, "order_items"):
        owed[item["order_id"]] += round(item["quantity"] * item["unit_price"] * 100) - round(
            item["discount_amount"] * 100
        )
    status = {}
    for order in rows(raw, "orders"):
        owed[order["order_id"]] += round(order["shipping_amount"] * 100)
        status[order["order_id"]] = order["status"].lower()
    paid = defaultdict(int)
    for p in rows(raw, "payments"):
        if p["status"] == "succeeded":
            paid[p["order_id"]] += p["amount_cents"] * (1 if p["payment_type"] == "charge" else -1)
    for order_id, cents in owed.items():
        expected = 0 if status[order_id] in ("cancelled", "returned") else cents
        assert paid[order_id] == expected, order_id


def test_raw_data_is_messy_on_purpose(late):
    statuses = late.tables["orders"]["status"]
    assert any(s != s.lower() for s in statuses)
    emails = late.tables["customers"]["email"]
    assert any(e != e.strip().lower() for e in emails)
    assert any(c != c.upper() for c in late.tables["customers"]["country_code"])
    event_ids = Counter(late.tables["web_events"]["event_id"])
    assert any(n > 1 for n in event_ids.values())


def test_tiers_only_go_up(early, late):
    rank = {"bronze": 0, "silver": 1, "gold": 2}
    before = {r["customer_id"]: r["loyalty_tier"] for r in rows(early, "customers")}
    for customer in rows(late, "customers"):
        if customer["customer_id"] in before:
            assert rank[customer["loyalty_tier"]] >= rank[before[customer["customer_id"]]]


def test_as_of_outside_the_period_is_rejected():
    with pytest.raises(ValueError):
        generate(SMALL, as_of=datetime(2030, 1, 1))
