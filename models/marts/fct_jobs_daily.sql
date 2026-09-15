select
    {{ dbt_utils.generate_surrogate_key(["date_day", "j.job_id"]) }} as job_daily_id,
    date_day,
    j.job_id
from {{ ref("dim_jobs") }} as j
cross join
    unnest(
        generate_date_array(
            j.date_added, if(j.is_active, current_date(), j.date_removed)
        )
    ) as date_day
