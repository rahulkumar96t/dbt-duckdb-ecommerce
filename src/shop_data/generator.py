"""Seeded generator for raw e-commerce extracts.

The whole timeline (``start`` .. ``end``) is simulated once from the seed; ``as_of`` only decides
what is *visible*: rows created later are dropped and mutable rows (orders, customers, products)
are shown in the state they had at ``as_of``. Two loads with different ``as_of`` dates therefore
describe the same shop at two points in time, which is what the SCD2 snapshot needs.

The raw data is deliberately a little messy, the way source systems are: mixed-case statuses,
untrimmed e-mails, lower-case country codes, payment amounts in minor units and duplicated web
events (at-least-once delivery). The staging layer cleans all of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import numpy as np

COUNTRIES = ["DE", "FR", "NL", "ES", "IT", "AT", "CH", "BE", "PL", "SE"]
COUNTRY_WEIGHTS = [0.24, 0.16, 0.10, 0.10, 0.10, 0.07, 0.07, 0.06, 0.06, 0.04]
CHANNELS = ["organic", "paid_search", "social", "referral", "email"]
CHANNEL_WEIGHTS = [0.35, 0.25, 0.20, 0.10, 0.10]
UTM_SOURCES = ["direct", "google", "newsletter", "instagram", "affiliate"]
UTM_WEIGHTS = [0.35, 0.30, 0.12, 0.15, 0.08]
FIRST_NAMES = [
    "Alex", "Sam", "Robin", "Kim", "Noa", "Luca", "Mia", "Jonas", "Emma", "Leo", "Nora",
    "Elias", "Lina", "Finn", "Ida", "Max", "Sofia", "Ben", "Clara", "Theo", "Ava", "Paul",
]  # fmt: skip
LAST_NAMES = [
    "Muller", "Martin", "Rossi", "Garcia", "Jansen", "Nowak", "Berg", "Weber", "Moreau",
    "Bianchi", "Lopez", "Visser", "Schmid", "Dubois", "Novak", "Lind", "Fischer", "Costa",
]  # fmt: skip
CATEGORIES = {  # category -> (median price, cost share)
    "apparel": (39.0, 0.45),
    "footwear": (79.0, 0.50),
    "accessories": (24.0, 0.35),
    "home": (49.0, 0.55),
    "beauty": (19.0, 0.40),
    "electronics": (129.0, 0.70),
}
ADJECTIVES = ["Classic", "Urban", "Nordic", "Everyday", "Studio", "Trail", "Soft", "Pro"]
NOUNS = {
    "apparel": ["Tee", "Hoodie", "Shirt", "Jacket", "Chinos"],
    "footwear": ["Sneaker", "Boot", "Runner", "Loafer"],
    "accessories": ["Cap", "Belt", "Scarf", "Tote", "Wallet"],
    "home": ["Mug", "Lamp", "Throw", "Vase", "Cushion"],
    "beauty": ["Balm", "Serum", "Cleanser", "Cream"],
    "electronics": ["Earbuds", "Speaker", "Charger", "Watch"],
}
PAYMENT_METHODS = ["card", "paypal", "klarna", "gift_card"]
TIERS = [("bronze", 0.0), ("silver", 300.0), ("gold", 1000.0)]
EPOCH = datetime(1970, 1, 1)


def _secs(value: datetime) -> float:
    """Seconds since the epoch for a naive timestamp, independent of the machine's time zone."""
    return (value - EPOCH).total_seconds()


@dataclass(frozen=True)
class GeneratorConfig:
    n_customers: int = 4_000
    n_products: int = 150
    start: datetime = datetime(2025, 1, 1)
    end: datetime = datetime(2026, 6, 30, 23, 59, 59)
    seed: int = 42
    anonymous_sessions_per_customer: float = 1.5
    duplicate_event_rate: float = 0.008


@dataclass
class RawTables:
    """Column-oriented raw tables: table name -> column name -> list of values."""

    tables: dict[str, dict[str, list]] = field(default_factory=dict)

    def rows(self, name: str) -> int:
        columns = self.tables[name]
        return len(next(iter(columns.values()))) if columns else 0


def _ts(rng: np.random.Generator, lo: datetime, hi: datetime) -> datetime:
    span = max((hi - lo).total_seconds(), 1.0)
    return (lo + timedelta(seconds=float(rng.uniform(0, span)))).replace(microsecond=0)


def _money(x: float) -> float:
    return round(float(x) + 1e-9, 2)


class _Shop:
    """Simulates the full timeline; :meth:`snapshot` projects it onto an ``as_of`` date."""

    def __init__(self, cfg: GeneratorConfig) -> None:
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.products: list[dict] = []
        self.customers: list[dict] = []
        self.orders: list[dict] = []
        self.items: list[dict] = []
        self.payments: list[dict] = []
        self.events: list[dict] = []
        self._make_products()
        self._make_customers_and_orders()
        self._make_browsing()

    # -- products --------------------------------------------------------------------------------
    def _make_products(self) -> None:
        rng, cfg = self.rng, self.cfg
        names = list(CATEGORIES)
        for pid in range(1, cfg.n_products + 1):
            category = names[int(rng.integers(len(names)))]
            median, cost_share = CATEGORIES[category]
            price = _money(np.round(median * rng.lognormal(0, 0.35)) - 0.01)
            created = _ts(rng, cfg.start - timedelta(days=365), cfg.start + timedelta(days=330))
            discontinued = (
                _ts(rng, created + timedelta(days=60), cfg.end + timedelta(days=200))
                if rng.random() < 0.12
                else None
            )
            noun = NOUNS[category][int(rng.integers(len(NOUNS[category])))]
            self.products.append(
                {
                    "product_id": pid,
                    "sku": f"SKU-{category[:3].upper()}-{pid:04d}",
                    "product_name": f"{ADJECTIVES[int(rng.integers(len(ADJECTIVES)))]} {noun}",
                    "category": category,
                    "unit_price": price,
                    "unit_cost": _money(price * cost_share * rng.uniform(0.85, 1.15)),
                    "created_at": created,
                    "discontinued_at": discontinued,
                    "popularity": float(rng.pareto(1.2) + 1.0),
                }
            )

        self._created = np.array([_secs(p["created_at"]) for p in self.products])
        self._gone = np.array(
            [_secs(p["discontinued_at"]) if p["discontinued_at"] else np.inf
             for p in self.products]
        )  # fmt: skip
        self._popularity = np.array([p["popularity"] for p in self.products])

    def _available_products(self, at: datetime) -> tuple[np.ndarray, np.ndarray]:
        t = _secs(at)
        idx = np.flatnonzero((self._created <= t) & (self._gone > t))
        weights = self._popularity[idx]
        return idx, weights / weights.sum()

    # -- customers, orders, payments, purchase sessions -------------------------------------------
    def _make_customers_and_orders(self) -> None:
        rng, cfg = self.rng, self.cfg
        horizon = (cfg.end - cfg.start).total_seconds()
        for cid in range(1, cfg.n_customers + 1):
            # sign-ups grow over time: density proportional to t
            signup = cfg.start + timedelta(seconds=float(np.sqrt(rng.random()) * horizon))
            signup = signup.replace(microsecond=0)
            first = FIRST_NAMES[int(rng.integers(len(FIRST_NAMES)))]
            last = LAST_NAMES[int(rng.integers(len(LAST_NAMES)))]
            customer = {
                "customer_id": cid,
                "first_name": first,
                "last_name": last,
                "email": f"{first}.{last}.{cid}@example.com".lower(),
                "country_code": str(rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS)),
                "acquisition_channel": str(rng.choice(CHANNELS, p=CHANNEL_WEIGHTS)),
                "signup_at": signup,
                "changes": [],  # (at, field, value)
                "preferred_method": str(rng.choice(PAYMENT_METHODS, p=[0.6, 0.25, 0.08, 0.07])),
                "messy_email": rng.random() < 0.04,
                "messy_country": rng.random() < 0.03,
            }
            if rng.random() < 0.03:
                when = _ts(rng, signup, cfg.end)
                customer["changes"].append((when, "email", f"{first}{cid}@mail.example.org"))
            if rng.random() < 0.015:
                when = _ts(rng, signup, cfg.end)
                customer["changes"].append((when, "country_code", str(rng.choice(COUNTRIES))))
            self.customers.append(customer)
            if rng.random() < 0.75:  # a quarter of sign-ups never buy
                self._orders_for(customer)
            customer["changes"].sort(key=lambda c: c[0])

    def _orders_for(self, customer: dict) -> None:
        rng, cfg = self.rng, self.cfg
        per_month = float(rng.gamma(1.6, 0.45))
        lifetime_days = float(rng.exponential(240))
        t = customer["signup_at"] + timedelta(hours=float(rng.exponential(72)))
        stop = min(customer["signup_at"] + timedelta(days=lifetime_days), cfg.end)
        spend, tier = 0.0, 0
        first = True
        while t <= cfg.end and (first or t <= stop):
            first = False
            order = self._order(customer, t.replace(microsecond=0))
            if order["cancelled_at"] is None:
                spend += order["order_total"]
                while tier + 1 < len(TIERS) and spend >= TIERS[tier + 1][1]:
                    tier += 1
                    upgrade = order["placed_at"] + timedelta(days=1)
                    customer["changes"].append((upgrade, "loyalty_tier", TIERS[tier][0]))
            gap_days = rng.exponential(30.0 / max(per_month, 0.05))
            t = t + timedelta(days=float(gap_days))

    def _order(self, customer: dict, placed: datetime) -> dict:
        rng = self.rng
        order_id = len(self.orders) + 1
        available, weights = self._available_products(placed)
        n_lines = min(1 + int(rng.poisson(0.8)), 6, len(available))
        chosen = rng.choice(available, size=n_lines, replace=False, p=weights)
        promo = rng.random() < 0.18
        subtotal = 0.0
        lines = []
        for idx in chosen:
            product = self.products[int(idx)]
            qty = 1 + min(int(rng.poisson(0.3)), 3)
            gross = qty * product["unit_price"]
            discount = _money(gross * rng.uniform(0.10, 0.25)) if promo else 0.0
            subtotal += gross - discount
            lines.append((product, qty, discount))
        subtotal = _money(subtotal)
        shipping = 0.0 if subtotal >= 50 else 4.95
        total = _money(subtotal + shipping)

        cancelled = shipped = delivered = returned = None
        if rng.random() < 0.035:
            cancelled = placed + timedelta(hours=float(rng.uniform(0.5, 20)))
        else:
            shipped = placed + timedelta(hours=float(rng.uniform(10, 72)))
            delivered = shipped + timedelta(hours=float(rng.uniform(24, 120)))
            if rng.random() < 0.06:
                returned = delivered + timedelta(days=float(rng.uniform(2, 25)))
        app = rng.random() < 0.35
        order = {
            "order_id": order_id,
            "customer_id": customer["customer_id"],
            "placed_at": placed,
            "shipped_at": shipped,
            "delivered_at": delivered,
            "cancelled_at": cancelled,
            "returned_at": returned,
            "shipping_amount": shipping,
            "order_total": total,
            "channel": "app" if app else "web",
            "messy_status": rng.random() < 0.05,
        }
        self.orders.append(order)
        for product, qty, discount in lines:
            self.items.append(
                {
                    "order_item_id": len(self.items) + 1,
                    "order_id": order_id,
                    "product_id": product["product_id"],
                    "quantity": qty,
                    "unit_price": product["unit_price"],
                    "discount_amount": discount,
                    "created_at": placed,
                }
            )
        self._payments_for(order, customer)
        self._purchase_session(order, [p for p, _, _ in lines], app)
        return order

    def _pay(self, order_id: int, method: str, kind: str, status: str, amount: float, at):
        self.payments.append(
            {
                "payment_id": len(self.payments) + 1,
                "order_id": order_id,
                "payment_method": method,
                "payment_type": kind,
                "status": status,
                "amount_cents": round(amount * 100),
                "created_at": at.replace(microsecond=0),
            }
        )

    def _payments_for(self, order: dict, customer: dict) -> None:
        rng = self.rng
        # payment is authorised at checkout, i.e. shortly *before* the order is placed
        t = order["placed_at"] - timedelta(seconds=float(rng.uniform(60, 400)))
        method = customer["preferred_method"]
        remaining = order["order_total"]
        charges: list[tuple[str, float]] = []
        if method == "gift_card":  # gift-card balance first, card for the rest
            balance = min(remaining, _money(rng.choice([10, 25, 50])))
            charges.append(("gift_card", balance))
            remaining = _money(remaining - balance)
            method = "card"
        if remaining > 0:
            charges.append((method, remaining))
        for m, amount in charges:
            if m != "gift_card" and rng.random() < 0.05:  # declined, then a successful retry
                self._pay(order["order_id"], m, "charge", "failed", amount, t)
                t += timedelta(seconds=float(rng.uniform(5, 20)))
            self._pay(order["order_id"], m, "charge", "succeeded", amount, t)
            t += timedelta(seconds=1)
        refund_at = order["cancelled_at"] or order["returned_at"]
        if refund_at is not None:
            for m, amount in charges:
                self._pay(order["order_id"], m, "refund", "succeeded", amount, refund_at)

    # -- web events ------------------------------------------------------------------------------
    def _session(self, start, customer_id, device, steps, gaps=None) -> None:
        rng = self.rng
        if gaps is None:
            gaps = rng.uniform(5, 240, size=len(steps))
        session_id = f"s{len(self.events):08d}{int(rng.integers(1_000)):03d}"
        anonymous_id = f"a{int(rng.integers(10**9)):09d}"
        utm = str(rng.choice(UTM_SOURCES, p=UTM_WEIGHTS))
        t = start
        for (event_type, product_id), gap in zip(steps, gaps, strict=False):
            self.events.append(
                {
                    "session_id": session_id,
                    "anonymous_id": anonymous_id,
                    "customer_id": customer_id,
                    "event_type": event_type,
                    "product_id": product_id,
                    "order_id": None,
                    "device": device,
                    "utm_source": utm,
                    "occurred_at": t.replace(microsecond=0),
                }
            )
            t += timedelta(seconds=float(gap))

    def _purchase_session(self, order: dict, products: list[dict], app: bool) -> None:
        rng = self.rng
        device = "app" if app else ("mobile_web" if rng.random() < 0.55 else "desktop")
        steps = [("page_view", None)]
        steps += [("product_view", p["product_id"]) for p in products]
        steps += [("add_to_cart", p["product_id"]) for p in products]
        steps += [("begin_checkout", None)]
        # choose the gaps first so that the purchase event lands exactly on the order time
        gaps = rng.uniform(5, 240, size=len(steps))
        start = order["placed_at"] - timedelta(seconds=float(gaps.sum()))
        self._session(start, order["customer_id"], device, steps, gaps)
        self.events.append(
            {
                **self.events[-1],
                "event_type": "purchase",
                "product_id": None,
                "order_id": order["order_id"],
                "occurred_at": order["placed_at"],
            }
        )

    def _browse_steps(self, available: np.ndarray, weights: np.ndarray) -> list[tuple]:
        rng = self.rng
        steps: list[tuple] = [("page_view", None)]
        if rng.random() < 0.6 and len(available):
            viewed = rng.choice(
                available,
                size=min(1 + int(rng.poisson(1.0)), len(available)),
                replace=False,
                p=weights,
            )
            steps += [("product_view", self.products[int(i)]["product_id"]) for i in viewed]
            if rng.random() < 0.3:
                steps.append(("add_to_cart", self.products[int(viewed[0])]["product_id"]))
                if rng.random() < 0.4:
                    steps.append(("begin_checkout", None))
        return steps

    def _make_browsing(self) -> None:
        rng, cfg = self.rng, self.cfg
        for customer in self.customers:
            active_days = (cfg.end - customer["signup_at"]).days
            for _ in range(int(rng.poisson(active_days / 30 * 1.2))):
                start = _ts(rng, customer["signup_at"], cfg.end)
                available, weights = self._available_products(start)
                device = str(rng.choice(["desktop", "mobile_web", "app"], p=[0.4, 0.45, 0.15]))
                self._session(
                    start, customer["customer_id"], device, self._browse_steps(available, weights)
                )
        for _ in range(int(cfg.n_customers * cfg.anonymous_sessions_per_customer)):
            start = _ts(rng, cfg.start, cfg.end)
            available, weights = self._available_products(start)
            device = str(rng.choice(["desktop", "mobile_web"], p=[0.45, 0.55]))
            self._session(start, None, device, self._browse_steps(available, weights))
        # at-least-once delivery: decide duplicates now so they do not depend on ``as_of``
        self.duplicate = rng.random(len(self.events)) < cfg.duplicate_event_rate
        self.ordered_events = sorted(
            range(len(self.events)), key=lambda i: (self.events[i]["occurred_at"], i)
        )

    # -- projection onto as_of -------------------------------------------------------------------
    def snapshot(self, as_of: datetime, loaded_at: datetime) -> RawTables:
        out = RawTables()

        def visible(ts):
            return ts if ts is not None and ts <= as_of else None

        def add(table: str, row: dict) -> None:
            cols = out.tables.setdefault(table, {})
            for key, value in {**row, "_loaded_at": loaded_at}.items():
                cols.setdefault(key, []).append(value)

        for c in self.customers:
            if c["signup_at"] > as_of:
                continue
            state = {
                "email": c["email"],
                "country_code": c["country_code"],
                "loyalty_tier": "bronze",
            }
            updated = c["signup_at"]
            for when, field_name, value in c["changes"]:
                if when <= as_of:
                    state[field_name], updated = value, max(updated, when)
            email = state["email"]
            if c["messy_email"]:
                email = f"  {email.upper()} "
            country = state["country_code"].lower() if c["messy_country"] else state["country_code"]
            add("customers", {
                "customer_id": c["customer_id"], "first_name": c["first_name"],
                "last_name": c["last_name"], "email": email, "country_code": country,
                "acquisition_channel": c["acquisition_channel"],
                "loyalty_tier": state["loyalty_tier"], "signup_at": c["signup_at"],
                "updated_at": updated,
            })  # fmt: skip

        for p in self.products:
            if p["created_at"] > as_of:
                continue
            gone = visible(p["discontinued_at"])
            add("products", {
                "product_id": p["product_id"], "sku": p["sku"], "product_name": p["product_name"],
                "category": p["category"], "unit_price": p["unit_price"],
                "unit_cost": p["unit_cost"], "is_active": gone is None,
                "created_at": p["created_at"], "updated_at": gone or p["created_at"],
            })  # fmt: skip

        visible_orders = set()
        for o in self.orders:
            if o["placed_at"] > as_of:
                continue
            visible_orders.add(o["order_id"])
            stamps = {
                k: visible(o[k])
                for k in ("shipped_at", "delivered_at", "cancelled_at", "returned_at")
            }
            status = "placed"
            for key, name in (
                ("cancelled_at", "cancelled"),
                ("shipped_at", "shipped"),
                ("delivered_at", "delivered"),
                ("returned_at", "returned"),
            ):
                if stamps[key] is not None:
                    status = name
            if o["messy_status"]:
                status = status.upper()
            add("orders", {
                "order_id": o["order_id"], "customer_id": o["customer_id"], "status": status,
                "channel": o["channel"], "placed_at": o["placed_at"], **stamps,
                "shipping_amount": o["shipping_amount"],
                "updated_at": max([o["placed_at"], *[v for v in stamps.values() if v]]),
            })  # fmt: skip

        for item in self.items:
            if item["order_id"] in visible_orders:
                add("order_items", item)
        for pay in self.payments:
            if pay["order_id"] in visible_orders and pay["created_at"] <= as_of:
                add("payments", pay)

        event_id = 0
        for i in self.ordered_events:
            event = self.events[i]
            if event["occurred_at"] > as_of:
                continue
            event_id += 1
            row = {"event_id": event_id, **event}
            add("web_events", row)
            if self.duplicate[i]:
                add("web_events", row)
        return out


def generate(
    cfg: GeneratorConfig | None = None,
    as_of: datetime | None = None,
    loaded_at: datetime | None = None,
) -> RawTables:
    """Simulate the shop for ``cfg`` and return the raw extracts visible at ``as_of``."""
    cfg = cfg or GeneratorConfig()
    as_of = as_of or cfg.end
    if not cfg.start < as_of <= cfg.end:
        raise ValueError(f"as_of must be within ({cfg.start}, {cfg.end}]")
    # naive UTC, which is how dbt source freshness interprets timestamps without a zone
    loaded_at = (loaded_at or datetime.now(UTC).replace(tzinfo=None)).replace(microsecond=0)
    return _Shop(cfg).snapshot(as_of, loaded_at)
