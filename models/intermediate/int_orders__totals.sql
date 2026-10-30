select
    order_id,
    count(*) as line_count,
    sum(quantity) as units,
    cast(sum(gross_amount) as decimal(12, 2)) as gross_amount,
    cast(sum(discount_amount) as decimal(12, 2)) as discount_amount,
    cast(sum(line_total) as decimal(12, 2)) as items_subtotal,
    cast(sum(cogs) as decimal(12, 2)) as cogs
from {{ ref('int_order_items__enriched') }}
group by order_id
