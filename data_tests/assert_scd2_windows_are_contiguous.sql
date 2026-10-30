-- Versions of a customer must tile time without gaps or overlaps:
-- each window ends exactly where the next one starts, and windows are not empty.
with ordered as (
    select
        customer_id,
        version_number,
        valid_from,
        valid_to,
        lead(valid_from) over (partition by customer_id order by version_number) as next_from
    from {{ ref('dim_customers_history') }}
)

select *
from ordered
where valid_from >= valid_to
   or (next_from is not null and next_from <> valid_to)
   or (next_from is null and valid_to <> timestamp '9999-12-31')
