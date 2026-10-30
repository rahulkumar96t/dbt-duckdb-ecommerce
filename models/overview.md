{% docs __overview__ %}
# Shop analytics

A reference analytics-engineering project on synthetic e-commerce data.

**Layers**

- `staging` (views): one model per raw table, renamed, typed and cleaned (case, whitespace,
  cents to decimals, duplicate events removed). No joins.
- `intermediate` (views): reusable building blocks: enriched order lines, order totals,
  payment summaries, sessions.
- `marts` (tables): facts and dimensions for analysis: `fct_orders`, `fct_order_items`,
  `dim_customers`, `dim_customers_history` (SCD2), `dim_products`,
  `customer_lifetime_value`, `fct_conversion_funnel`, `fct_cohort_retention`.
- `snapshots`: `snap_customers` keeps the type-2 history of the customer record.

Raw parquet files are read in place by DuckDB (dbt-duckdb `external_location`), so there is
no load step and no server.
{% enddocs %}
