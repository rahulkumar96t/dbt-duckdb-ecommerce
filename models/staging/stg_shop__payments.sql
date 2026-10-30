with source as (
    select * from {{ source('shop', 'payments') }}
)

select
    payment_id,
    order_id,
    payment_method,
    payment_type,
    status as payment_status,
    {{ cents_to_amount('amount_cents') }} as amount,
    created_at
from source
