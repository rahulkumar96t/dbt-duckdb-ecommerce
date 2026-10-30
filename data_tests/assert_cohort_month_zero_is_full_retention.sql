-- By definition every cohort member is active in the cohort month.
select cohort_month, cohort_size, active_customers
from {{ ref('fct_cohort_retention') }}
where month_number = 0 and active_customers <> cohort_size
