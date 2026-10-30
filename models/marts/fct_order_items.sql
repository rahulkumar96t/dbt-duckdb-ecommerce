with items as (
    select * from {{ ref('int_order_items__enriched') }}
),

orders as (
    select order_id, customer_id, placed_at, order_date, order_month, order_status, is_reversed
    from {{ ref('fct_orders') }}
)

select
    items.order_item_id,
    items.order_id,
    orders.customer_id,
    items.product_id,
    items.product_name,
    items.category,
    orders.placed_at,
    orders.order_date,
    orders.order_month,
    orders.order_status,
    orders.is_reversed,
    items.quantity,
    items.unit_price,
    items.gross_amount,
    items.discount_amount,
    items.line_total,
    items.cogs,
    cast(case when orders.is_reversed then 0 else items.line_total end as decimal(12, 2))
        as net_revenue,
    cast(case when orders.is_reversed then 0 else items.gross_margin end as decimal(12, 2))
        as gross_margin
from items
inner join orders on items.order_id = orders.order_id
