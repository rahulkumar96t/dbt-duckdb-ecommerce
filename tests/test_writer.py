from __future__ import annotations

import duckdb

from shop_data.writer import SCHEMAS, write_parquet


def test_parquet_round_trip(tmp_path, late):
    counts = write_parquet(late, tmp_path)
    assert set(counts) == set(SCHEMAS)
    con = duckdb.connect()
    for name, schema in SCHEMAS.items():
        path = tmp_path / f"{name}.parquet"
        n = con.sql(f"select count(*) from read_parquet('{path}')").fetchall()[0][0]
        assert n == counts[name] == late.rows(name)
        columns = [
            r[0] for r in con.sql(f"describe select * from read_parquet('{path}')").fetchall()
        ]
        assert columns == schema.names
    described = con.sql(
        f"describe select * from read_parquet('{tmp_path / 'payments.parquet'}')"
    ).fetchall()
    kinds = {row[0]: row[1] for row in described}
    assert kinds["amount_cents"] == "BIGINT"
