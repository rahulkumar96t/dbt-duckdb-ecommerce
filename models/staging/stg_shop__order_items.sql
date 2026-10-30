with source as (
    select * from {{ source('shop', 'order_items') }}
)

select
    order_item_id,
    order_id,
    product_id,
    quantity,
    {{ money('unit_price') }} as unit_price,
    {{ money('discount_amount') }} as discount_amount,
    cast(quantity * {{ money('unit_price') }} as decimal(12, 2)) as gross_amount,
    cast(quantity * {{ money('unit_price') }} - {{ money('discount_amount') }} as decimal(12, 2))
        as line_total
from source
