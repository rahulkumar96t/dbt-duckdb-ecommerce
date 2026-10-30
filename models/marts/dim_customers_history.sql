{#
    SCD2 view of customers built from the snapshot.

    The snapshot starts observing at the first run, so the oldest version of a customer is
    stretched back to 1900-01-01: it is the best available estimate for any earlier fact
    (for example an order placed before the first snapshot). `recorded_from` keeps the real
    observation time.
#}
with snapshot as (
    select * from {{ ref('snap_customers') }}
),

versions as (
    select
        dbt_scd_id as customer_version_id,
        customer_id,
        {{ clean_email('email') }} as email,
        {{ clean_country('country_code') }} as country_code,
        loyalty_tier,
        dbt_valid_from as recorded_from,
        dbt_valid_to,
        row_number() over (partition by customer_id order by dbt_valid_from) as version_number
    from snapshot
)

select
    customer_version_id,
    customer_id,
    version_number,
    email,
    country_code,
    loyalty_tier,
    recorded_from,
    case when version_number = 1 then timestamp '1900-01-01' else recorded_from end as valid_from,
    coalesce(dbt_valid_to, timestamp '9999-12-31') as valid_to,
    dbt_valid_to is null as is_current
from versions
