-- Customer-level revenue must add up to order-level revenue (no customers lost or doubled).
with clv as (select sum(net_revenue) as revenue from {{ ref('customer_lifetime_value') }}),
     orders as (select sum(net_revenue) as revenue from {{ ref('fct_orders') }})
select clv.revenue as clv_revenue, orders.revenue as order_revenue
from clv cross join orders
where clv.revenue <> orders.revenue
