{#
    Monthly cohort retention. A customer belongs to the cohort of the month of their first
    order (cancelled orders do not count as activity) and is "retained" in month n if they
    placed a non-cancelled order n calendar months later. Every cohort gets a row for every
    month up to the last month in the data, so zero-retention months are explicit.
#}
with orders as (
    select customer_id, order_month, net_revenue
    from {{ ref('fct_orders') }}
    where not is_cancelled
),

cohorts as (
    select customer_id, min(order_month) as cohort_month
    from orders
    group by customer_id
),

cohort_sizes as (
    select cohort_month, count(*) as cohort_size
    from cohorts
    group by cohort_month
),

last_month as (
    select max(order_month) as last_month from orders
),

spine as (
    select
        cohort_sizes.cohort_month,
        cohort_sizes.cohort_size,
        unnest(range(0, date_diff('month', cohort_sizes.cohort_month, last_month.last_month) + 1))
            as month_number
    from cohort_sizes
    cross join last_month
),

activity as (
    select
        cohorts.cohort_month,
        date_diff('month', cohorts.cohort_month, orders.order_month) as month_number,
        count(distinct orders.customer_id) as active_customers,
        sum(orders.net_revenue) as net_revenue
    from orders
    inner join cohorts on orders.customer_id = cohorts.customer_id
    group by all
)

select
    spine.cohort_month,
    spine.month_number,
    cast(spine.cohort_month + to_months(cast(spine.month_number as integer)) as date)
        as activity_month,
    spine.cohort_size,
    coalesce(activity.active_customers, 0) as active_customers,
    coalesce(activity.active_customers, 0) / spine.cohort_size as retention_rate,
    cast(coalesce(activity.net_revenue, 0) as decimal(12, 2)) as net_revenue,
    sum(coalesce(activity.net_revenue, 0)) over (
        partition by spine.cohort_month order by spine.month_number
    ) / spine.cohort_size as cumulative_revenue_per_customer
from spine
left join activity
    on spine.cohort_month = activity.cohort_month
    and spine.month_number = activity.month_number
