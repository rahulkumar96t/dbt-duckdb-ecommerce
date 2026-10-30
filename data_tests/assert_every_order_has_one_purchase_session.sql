-- Orders and purchase sessions must match one to one (tracking completeness).
with purchases as (
    select order_id, count(*) as sessions
    from {{ ref('int_web__sessions') }}
    where has_purchase
    group by order_id
)

select orders.order_id, coalesce(purchases.sessions, 0) as purchase_sessions
from {{ ref('fct_orders') }} as orders
full outer join purchases on orders.order_id = purchases.order_id
where orders.order_id is null or coalesce(purchases.sessions, 0) <> 1
