with source as (
    select * from {{ source('shop', 'customers') }}
)

select
    customer_id,
    first_name,
    last_name,
    {{ clean_email('email') }} as email,
    {{ clean_country('country_code') }} as country_code,
    acquisition_channel,
    loyalty_tier,
    signup_at,
    updated_at
from source
