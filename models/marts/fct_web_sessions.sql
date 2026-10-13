with
    active_job_page_views as (
        select
            e.session_id as source_session_id,
            countif(
                e.event_type = "page_view"
                and date(e.event_ts)
                between j.date_added and if(j.is_active, current_date(), j.date_removed)
            ) as active_job_page_view_count
        from {{ ref("stg_posthog__events") }} as e
        left join
            {{ ref("dim_jobs") }} as j
            on e.organization_slug = j.organization_slug
            and e.job_slug = j.job_slug
        where e.session_id is not null
        group by e.session_id
    )

select
    s.session_id,
    s.session_started_ts,
    s.page_view_count,
    s.distinct_page_count,
    a.active_job_page_view_count,
    s.apply_click_count,
    a.active_job_page_view_count > 0
    and (s.distinct_page_count >= 2 or s.apply_click_count > 0) as is_engaged_job_seeker
from {{ ref("int_web_sessions") }} as s
left join active_job_page_views as a on s.source_session_id = a.source_session_id
