from __future__ import annotations

from datetime import datetime

import pytest

from shop_data.generator import GeneratorConfig, RawTables, generate

SMALL = GeneratorConfig(n_customers=400, n_products=60, seed=7)
EARLY = datetime(2026, 3, 31, 23, 59, 59)
LOADED_AT = datetime(2026, 7, 1, 6, 0, 0)


@pytest.fixture(scope="session")
def small_config() -> GeneratorConfig:
    return SMALL


@pytest.fixture(scope="session")
def late() -> RawTables:
    return generate(SMALL, loaded_at=LOADED_AT)


@pytest.fixture(scope="session")
def early() -> RawTables:
    return generate(SMALL, as_of=EARLY, loaded_at=LOADED_AT)


def rows(raw: RawTables, table: str) -> list[dict]:
    columns = raw.tables[table]
    names = list(columns)
    return [dict(zip(names, values, strict=True)) for values in zip(*columns.values(), strict=True)]
