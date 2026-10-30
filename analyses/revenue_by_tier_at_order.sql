-- Compiled by `dbt compile` (target/compiled/...), not materialised.
-- Monthly revenue split by the loyalty tier the customer had *when ordering*, which needs the
-- SCD2 history: using today's tier would credit early orders to the customer's current tier.
select
    order_month,
    loyalty_tier_at_order,
    count(*) as orders,
    sum(net_revenue) as net_revenue,
    round(avg(net_revenue), 2) as avg_net_revenue
from {{ ref('fct_orders') }}
where not is_reversed
group by order_month, loyalty_tier_at_order
order by order_month, loyalty_tier_at_order
