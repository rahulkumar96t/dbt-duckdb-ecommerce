select orders.order_id, orders.placed_at, customers.signup_at
from {{ ref('fct_orders') }} as orders
inner join {{ ref('dim_customers') }} as customers on orders.customer_id = customers.customer_id
where orders.placed_at < customers.signup_at
