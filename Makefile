# Raw extracts and the DuckDB file; override on the command line if needed.
export SHOP_RAW_DIR ?= data/raw
export SHOP_DUCKDB_PATH ?= warehouse/shop.duckdb

DBT := uv run dbt
DBT_FLAGS := --profiles-dir .

.PHONY: install data build docs docs-serve history test lint clean warehouse

install:
	uv sync --locked

# Raw parquet extracts as of the end of the simulated period.
data:
	uv run shop-data generate --out $(SHOP_RAW_DIR)

# Source freshness + models, snapshot, unit and data tests in DAG order.
build: warehouse
	$(DBT) source freshness $(DBT_FLAGS)
	$(DBT) build $(DBT_FLAGS)

docs: warehouse
	$(DBT) docs generate $(DBT_FLAGS)

docs-serve: docs
	$(DBT) docs serve $(DBT_FLAGS) --port 8080

# Two loads a month apart: the second build's snapshot records real customer changes (SCD2).
history: warehouse
	uv run shop-data generate --out $(SHOP_RAW_DIR) --as-of 2026-05-31
	$(DBT) build $(DBT_FLAGS)
	uv run shop-data generate --out $(SHOP_RAW_DIR)
	$(DBT) source freshness $(DBT_FLAGS)
	$(DBT) build $(DBT_FLAGS)

test:
	uv run pytest -q

lint:
	uv run ruff format --check .
	uv run ruff check .

warehouse:
	@mkdir -p $(dir $(SHOP_DUCKDB_PATH))

clean:
	rm -rf data warehouse target logs .pytest_cache .ruff_cache
