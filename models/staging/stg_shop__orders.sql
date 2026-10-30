with source as (
    select * from {{ source('shop', 'orders') }}
)

select
    order_id,
    customer_id,
    lower(trim(status)) as order_status,
    channel,
    placed_at,
    cast(placed_at as date) as order_date,
    shipped_at,
    delivered_at,
    cancelled_at,
    returned_at,
    {{ money('shipping_amount') }} as shipping_amount,
    updated_at
from source
