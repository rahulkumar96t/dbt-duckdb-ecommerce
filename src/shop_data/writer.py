"""Write :class:`RawTables` as parquet files with explicit, stable schemas."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from shop_data.generator import RawTables

TS = pa.timestamp("us")

SCHEMAS: dict[str, pa.Schema] = {
    "customers": pa.schema(
        [
            ("customer_id", pa.int64()),
            ("first_name", pa.string()),
            ("last_name", pa.string()),
            ("email", pa.string()),
            ("country_code", pa.string()),
            ("acquisition_channel", pa.string()),
            ("loyalty_tier", pa.string()),
            ("signup_at", TS),
            ("updated_at", TS),
            ("_loaded_at", TS),
        ]
    ),
    "products": pa.schema(
        [
            ("product_id", pa.int64()),
            ("sku", pa.string()),
            ("product_name", pa.string()),
            ("category", pa.string()),
            ("unit_price", pa.float64()),
            ("unit_cost", pa.float64()),
            ("is_active", pa.bool_()),
            ("created_at", TS),
            ("updated_at", TS),
            ("_loaded_at", TS),
        ]
    ),
    "orders": pa.schema(
        [
            ("order_id", pa.int64()),
            ("customer_id", pa.int64()),
            ("status", pa.string()),
            ("channel", pa.string()),
            ("placed_at", TS),
            ("shipped_at", TS),
            ("delivered_at", TS),
            ("cancelled_at", TS),
            ("returned_at", TS),
            ("shipping_amount", pa.float64()),
            ("updated_at", TS),
            ("_loaded_at", TS),
        ]
    ),
    "order_items": pa.schema(
        [
            ("order_item_id", pa.int64()),
            ("order_id", pa.int64()),
            ("product_id", pa.int64()),
            ("quantity", pa.int32()),
            ("unit_price", pa.float64()),
            ("discount_amount", pa.float64()),
            ("created_at", TS),
            ("_loaded_at", TS),
        ]
    ),
    "payments": pa.schema(
        [
            ("payment_id", pa.int64()),
            ("order_id", pa.int64()),
            ("payment_method", pa.string()),
            ("payment_type", pa.string()),
            ("status", pa.string()),
            ("amount_cents", pa.int64()),
            ("created_at", TS),
            ("_loaded_at", TS),
        ]
    ),
    "web_events": pa.schema(
        [
            ("event_id", pa.int64()),
            ("session_id", pa.string()),
            ("anonymous_id", pa.string()),
            ("customer_id", pa.int64()),
            ("event_type", pa.string()),
            ("product_id", pa.int64()),
            ("order_id", pa.int64()),
            ("device", pa.string()),
            ("utm_source", pa.string()),
            ("occurred_at", TS),
            ("_loaded_at", TS),
        ]
    ),
}


def to_arrow(raw: RawTables) -> dict[str, pa.Table]:
    tables = {}
    for name, schema in SCHEMAS.items():
        columns = raw.tables.get(name, {})
        tables[name] = pa.table({f.name: columns.get(f.name, []) for f in schema}, schema=schema)
    return tables


def write_parquet(raw: RawTables, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, table in to_arrow(raw).items():
        pq.write_table(table, out_dir / f"{name}.parquet")
        counts[name] = table.num_rows
    return counts
