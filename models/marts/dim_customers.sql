{#
    Current customer attributes plus order behaviour. Recency is measured against the latest
    order in the data (not the wall clock) so that results are reproducible for a given load.
#}
with customers as (
    select * from {{ ref('stg_shop__customers') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
),

reference as (
    select max(placed_at) as as_of from orders
),

order_stats as (
    select
        customer_id,
        min(placed_at) as first_order_at,
        max(placed_at) as last_order_at,
        count(*) as orders_placed,
        count(*) filter (where not is_reversed) as orders_kept,
        sum(net_revenue) as lifetime_net_revenue,
        sum(gross_margin) as lifetime_gross_margin
    from orders
    group by customer_id
)

select
    customers.customer_id,
    customers.first_name,
    customers.last_name,
    customers.email,
    customers.country_code,
    customers.acquisition_channel,
    customers.loyalty_tier,
    customers.signup_at,
    cast(date_trunc('month', order_stats.first_order_at) as date) as cohort_month,
    order_stats.first_order_at,
    order_stats.last_order_at,
    coalesce(order_stats.orders_placed, 0) as orders_placed,
    coalesce(order_stats.orders_kept, 0) as orders_kept,
    cast(coalesce(order_stats.lifetime_net_revenue, 0) as decimal(12, 2)) as lifetime_net_revenue,
    cast(coalesce(order_stats.lifetime_gross_margin, 0) as decimal(12, 2))
        as lifetime_gross_margin,
    date_diff('day', order_stats.last_order_at, reference.as_of) as days_since_last_order,
    case
        when order_stats.customer_id is null then 'prospect'
        when date_diff('day', order_stats.last_order_at, reference.as_of)
            <= {{ var('lapsed_after_days') }} then 'active'
        when date_diff('day', order_stats.last_order_at, reference.as_of)
            <= {{ var('churned_after_days') }} then 'lapsed'
        else 'churned'
    end as lifecycle_status
from customers
cross join reference
left join order_stats on customers.customer_id = order_stats.customer_id
