with source as (
    select * from {{ source('shop', 'products') }}
)

select
    product_id,
    sku,
    product_name,
    category,
    {{ money('unit_price') }} as unit_price,
    {{ money('unit_cost') }} as unit_cost,
    is_active,
    created_at,
    updated_at
from source
