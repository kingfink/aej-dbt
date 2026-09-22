with
    session_outcomes as (
        select
            e.session_id,
            logical_or(
                e.event_type = "page_view" and active_job.job_daily_id is not null
            ) as has_active_job_view,
            logical_or(e.event_type = "apply_click") as has_apply_click
        from {{ ref("fct_web_events") }} as e
        left join
            {{ ref("fct_jobs_daily") }} as active_job
            on e.job_id = active_job.job_id
            and date(e.event_ts) = active_job.date_day
        where e.session_id is not null
        group by 1
    )

select
    s.session_id,
    s.session_started_ts,
    coalesce(o.has_active_job_view, false) as has_active_job_view,
    coalesce(o.has_apply_click, false) as has_apply_click
from {{ ref("dim_web_sessions") }} as s
left join session_outcomes as o on s.session_id = o.session_id
