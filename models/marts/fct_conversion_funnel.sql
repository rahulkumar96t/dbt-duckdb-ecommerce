with sessions as (
    select * from {{ ref('int_web__sessions') }}
),

daily as (
    select
        cast(session_started_at as date) as session_date,
        device,
        utm_source,
        count(*) as sessions,
        count(*) filter (where customer_id is not null) as logged_in_sessions,
        count(*) filter (where has_product_view) as product_view_sessions,
        count(*) filter (where has_add_to_cart) as add_to_cart_sessions,
        count(*) filter (where has_checkout) as checkout_sessions,
        count(*) filter (where has_purchase) as purchase_sessions
    from sessions
    group by all
)

select
    *,
    {{ safe_divide('product_view_sessions', 'sessions') }} as view_rate,
    {{ safe_divide('add_to_cart_sessions', 'product_view_sessions') }} as view_to_cart_rate,
    {{ safe_divide('checkout_sessions', 'add_to_cart_sessions') }} as cart_to_checkout_rate,
    {{ safe_divide('purchase_sessions', 'checkout_sessions') }} as checkout_to_purchase_rate,
    {{ safe_divide('purchase_sessions', 'sessions') }} as session_conversion_rate
from daily
