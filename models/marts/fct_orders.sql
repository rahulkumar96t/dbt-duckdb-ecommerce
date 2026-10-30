with orders as (
    select * from {{ ref('stg_shop__orders') }}
),

totals as (
    select * from {{ ref('int_orders__totals') }}
),

payments as (
    select * from {{ ref('int_payments__order_summary') }}
),

purchase_sessions as (
    select order_id, device, utm_source
    from {{ ref('int_web__sessions') }}
    where order_id is not null
),

customer_versions as (
    select * from {{ ref('dim_customers_history') }}
),

joined as (
    select
        orders.order_id,
        orders.customer_id,
        orders.order_status,
        orders.channel,
        orders.placed_at,
        orders.order_date,
        cast(date_trunc('month', orders.placed_at) as date) as order_month,
        totals.line_count,
        totals.units,
        totals.gross_amount,
        totals.discount_amount,
        totals.items_subtotal,
        orders.shipping_amount,
        cast(totals.items_subtotal + orders.shipping_amount as decimal(12, 2)) as order_total,
        totals.cogs,
        orders.order_status in ('cancelled', 'returned') as is_reversed,
        orders.order_status = 'cancelled' as is_cancelled,
        orders.order_status = 'returned' as is_returned,
        coalesce(payments.charged_amount, 0) as charged_amount,
        coalesce(payments.refunded_amount, 0) as refunded_amount,
        coalesce(payments.net_paid, 0) as net_paid,
        coalesce(payments.failed_charges, 0) as failed_charges,
        payments.payment_methods,
        purchase_sessions.device as purchase_device,
        purchase_sessions.utm_source as purchase_utm_source,
        customer_versions.loyalty_tier as loyalty_tier_at_order,
        customer_versions.country_code as country_code_at_order
    from orders
    inner join totals on orders.order_id = totals.order_id
    left join payments on orders.order_id = payments.order_id
    left join purchase_sessions on orders.order_id = purchase_sessions.order_id
    left join customer_versions
        on orders.customer_id = customer_versions.customer_id
        and orders.placed_at >= customer_versions.valid_from
        and orders.placed_at < customer_versions.valid_to
),

sequenced as (
    select
        *,
        row_number() over (partition by customer_id order by placed_at, order_id)
            as customer_order_number,
        date_diff(
            'day',
            lag(placed_at) over (partition by customer_id order by placed_at, order_id),
            placed_at
        ) as days_since_previous_order
    from joined
)

select
    *,
    customer_order_number = 1 as is_first_order,
    cast(case when is_reversed then 0 else items_subtotal end as decimal(12, 2)) as net_revenue,
    cast(case when is_reversed then 0 else items_subtotal - cogs end as decimal(12, 2))
        as gross_margin
from sequenced
