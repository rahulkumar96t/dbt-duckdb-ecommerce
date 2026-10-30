-- A session cannot purchase without checkout, check out without a cart, or add to cart
-- without viewing a product. Step flags come straight from events, so this catches tracking gaps.
select *
from {{ ref('fct_conversion_funnel') }}
where not (
    sessions >= product_view_sessions
    and product_view_sessions >= add_to_cart_sessions
    and add_to_cart_sessions >= checkout_sessions
    and checkout_sessions >= purchase_sessions
)
