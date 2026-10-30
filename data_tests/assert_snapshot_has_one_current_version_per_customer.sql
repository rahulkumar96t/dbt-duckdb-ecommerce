-- Every customer in the latest extract has exactly one open version in the snapshot.
with current_versions as (
    select customer_id, count(*) as open_versions
    from {{ ref('snap_customers') }}
    where dbt_valid_to is null
    group by customer_id
)

select customers.customer_id, coalesce(current_versions.open_versions, 0) as open_versions
from {{ ref('stg_shop__customers') }} as customers
left join current_versions on customers.customer_id = current_versions.customer_id
where coalesce(current_versions.open_versions, 0) <> 1
