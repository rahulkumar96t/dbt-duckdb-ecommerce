"""Run the real dbt project twice (two loads) against a temporary DuckDB file."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from shop_data.generator import generate
from shop_data.writer import write_parquet
from tests.conftest import EARLY, SMALL

dbt_main = pytest.importorskip("dbt.cli.main")

PROJECT = Path(__file__).resolve().parents[1]


def _dbt(args: list[str], tmp: Path) -> None:
    common = {
        "--project-dir": PROJECT,
        "--profiles-dir": PROJECT,
        "--target-path": tmp / "target",
        "--log-path": tmp / "logs",
    }
    flags = [part for flag, value in common.items() for part in (flag, str(value))]
    result = dbt_main.dbtRunner().invoke([*args, *flags, "--quiet"])
    assert result.success, result.exception or result.result


@pytest.mark.dbt
def test_two_loads_build_and_capture_history(tmp_path, monkeypatch):
    raw_dir, db = tmp_path / "raw", tmp_path / "shop.duckdb"
    monkeypatch.setenv("SHOP_RAW_DIR", str(raw_dir))
    monkeypatch.setenv("SHOP_DUCKDB_PATH", str(db))

    write_parquet(generate(SMALL, as_of=EARLY), raw_dir)
    _dbt(["build"], tmp_path)
    write_parquet(generate(SMALL), raw_dir)
    _dbt(["source", "freshness"], tmp_path)
    _dbt(["build"], tmp_path)

    # dbt-duckdb keeps its in-process database open read-write; match that configuration
    con = duckdb.connect(str(db))

    def one(sql: str):
        # duckdb>=2: a relation re-executes on every fetch, so fetch once and index
        return con.sql(sql).fetchall()[0]

    raw_orders = one(f"select count(*) from read_parquet('{raw_dir / 'orders.parquet'}')")[0]
    assert one("select count(*) from marts.fct_orders")[0] == raw_orders

    closed, customers_with_history = one(
        "select count(*) filter (where dbt_valid_to is not null), "
        "count(distinct customer_id) filter (where dbt_valid_to is not null) "
        "from snapshots.snap_customers"
    )
    assert closed > 0 and customers_with_history > 0

    # point-in-time join: a customer upgraded after the first load keeps the old tier on
    # orders placed before the upgrade
    mismatched = one(
        """
        select count(*)
        from marts.fct_orders o
        join marts.dim_customers c using (customer_id)
        where o.loyalty_tier_at_order <> c.loyalty_tier
        """
    )[0]
    assert mismatched > 0

    month0 = con.sql(
        "select distinct retention_rate from marts.fct_cohort_retention where month_number = 0"
    ).fetchall()
    assert month0 == [(1.0,)]

    events = raw_dir / "web_events.parquet"
    dupes = one(f"select count(*) - count(distinct event_id) from read_parquet('{events}')")[0]
    staged = one("select count(*) - count(distinct event_id) from staging.stg_web__events")[0]
    assert dupes > 0 and staged == 0
