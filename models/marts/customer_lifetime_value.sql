{#
    Historical customer value plus RFM scoring.

    `expected_12m_margin` is deliberately naive: the customer's average monthly gross margin
    since the first order, times 12, for customers who are still active (zero otherwise).
    It is a transparent placeholder for a probabilistic model (BG/NBD + Gamma-Gamma), not one.
#}
with customers as (
    select * from {{ ref('dim_customers') }}
    where orders_placed > 0
),

frequency as (
    select customer_id, count(*) filter (where not is_reversed) as kept_orders
    from {{ ref('fct_orders') }}
    group by customer_id
),

base as (
    select
        customers.customer_id,
        customers.cohort_month,
        customers.first_order_at,
        customers.last_order_at,
        customers.lifecycle_status,
        customers.days_since_last_order as recency_days,
        frequency.kept_orders,
        customers.lifetime_net_revenue as net_revenue,
        customers.lifetime_gross_margin as gross_margin,
        greatest(date_diff('day', customers.first_order_at, customers.last_order_at), 0)
            as active_span_days,
        greatest(
            date_diff('day', customers.first_order_at, customers.last_order_at)
            + customers.days_since_last_order,
            1
        ) as tenure_days
    from customers
    inner join frequency on customers.customer_id = frequency.customer_id
),

scored as (
    select
        *,
        {{ safe_divide('net_revenue', 'kept_orders') }} as avg_order_value,
        kept_orders / (tenure_days / 30.4375) as orders_per_month,
        ntile(5) over (order by recency_days desc, customer_id) as recency_score,
        ntile(5) over (order by kept_orders, customer_id) as frequency_score,
        ntile(5) over (order by net_revenue, customer_id) as monetary_score
    from base
)

select
    customer_id,
    cohort_month,
    first_order_at,
    last_order_at,
    lifecycle_status,
    tenure_days,
    recency_days,
    kept_orders,
    net_revenue,
    gross_margin,
    avg_order_value,
    orders_per_month,
    recency_score,
    frequency_score,
    monetary_score,
    case
        when recency_score >= 4 and frequency_score >= 4 then 'champion'
        when frequency_score >= 4 then 'loyal'
        when recency_score <= 2 and frequency_score >= 3 then 'at_risk'
        when recency_score >= 4 and frequency_score <= 2 then 'new_or_promising'
        when recency_score <= 2 and frequency_score <= 2 then 'hibernating'
        else 'needs_attention'
    end as rfm_segment,
    gross_margin as historical_clv,
    cast(
        case
            when lifecycle_status = 'active'
                then gross_margin / (tenure_days / 30.4375) * 12
            else 0
        end as decimal(12, 2)
    ) as expected_12m_margin
from scored
