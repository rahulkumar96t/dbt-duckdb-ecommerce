with items as (
    select * from {{ ref('stg_shop__order_items') }}
),

products as (
    select * from {{ ref('stg_shop__products') }}
)

select
    items.order_item_id,
    items.order_id,
    items.product_id,
    products.product_name,
    products.category,
    items.quantity,
    items.unit_price,
    items.discount_amount,
    items.gross_amount,
    items.line_total,
    cast(items.quantity * products.unit_cost as decimal(12, 2)) as cogs,
    cast(items.line_total - items.quantity * products.unit_cost as decimal(12, 2)) as gross_margin
from items
inner join products on items.product_id = products.product_id
