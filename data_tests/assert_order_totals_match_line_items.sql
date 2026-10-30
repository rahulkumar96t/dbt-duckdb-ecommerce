-- The order-level subtotal must equal the sum of its lines in fct_order_items.
with lines as (
    select order_id, sum(line_total) as lines_total
    from {{ ref('fct_order_items') }}
    group by order_id
)

select orders.order_id, orders.items_subtotal, lines.lines_total
from {{ ref('fct_orders') }} as orders
left join lines on orders.order_id = lines.order_id
where lines.lines_total is null or orders.items_subtotal <> lines.lines_total
