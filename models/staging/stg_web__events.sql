{#
    The tracker delivers events at least once, so the same event can arrive twice.
    Keep one row per event_id (the earliest load wins; rows are otherwise identical).
#}
with source as (
    select * from {{ source('web', 'events') }}
),

deduplicated as (
    select *
    from source
    qualify row_number() over (partition by event_id order by _loaded_at) = 1
)

select
    event_id,
    session_id,
    anonymous_id,
    customer_id,
    event_type,
    product_id,
    order_id,
    device,
    utm_source,
    occurred_at
from deduplicated
