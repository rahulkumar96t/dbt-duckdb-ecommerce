with events as (
    select * from {{ ref('stg_web__events') }}
)

select
    session_id,
    max(customer_id) as customer_id,
    arg_min(anonymous_id, occurred_at) as anonymous_id,
    arg_min(device, occurred_at) as device,
    arg_min(utm_source, occurred_at) as utm_source,
    min(occurred_at) as session_started_at,
    max(occurred_at) as session_ended_at,
    count(*) as event_count,
    bool_or(event_type = 'product_view') as has_product_view,
    bool_or(event_type = 'add_to_cart') as has_add_to_cart,
    bool_or(event_type = 'begin_checkout') as has_checkout,
    bool_or(event_type = 'purchase') as has_purchase,
    max(order_id) as order_id
from events
group by session_id
