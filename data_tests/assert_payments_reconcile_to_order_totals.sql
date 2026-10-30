-- Money in must match money owed: for every order, succeeded charges minus succeeded refunds
-- equal the order total, or zero once the order was cancelled or returned.
select
    order_id,
    order_status,
    order_total,
    charged_amount,
    refunded_amount,
    net_paid
from {{ ref('fct_orders') }}
where abs(net_paid - case when is_reversed then 0 else order_total end) > 0.005
