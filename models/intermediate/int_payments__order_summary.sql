with payments as (
    select * from {{ ref('stg_shop__payments') }}
),

flagged as (
    select
        *,
        payment_type = 'charge' and payment_status = 'succeeded' as is_captured,
        payment_type = 'refund' and payment_status = 'succeeded' as is_refunded
    from payments
)

select
    order_id,
    count(*) as payment_events,
    count(*) filter (where payment_type = 'charge' and payment_status = 'failed')
        as failed_charges,
    cast(coalesce(sum(amount) filter (where is_captured), 0) as decimal(12, 2)) as charged_amount,
    cast(coalesce(sum(amount) filter (where is_refunded), 0) as decimal(12, 2)) as refunded_amount,
    cast(
        coalesce(sum(amount) filter (where is_captured), 0)
        - coalesce(sum(amount) filter (where is_refunded), 0)
        as decimal(12, 2)
    ) as net_paid,
    string_agg(distinct payment_method, ',' order by payment_method) filter (where is_captured)
        as payment_methods,
    min(created_at) filter (where is_captured) as first_captured_at
from flagged
group by order_id
