select
    e.event_id,
    e.source_event_id,
    e.source,
    e.event_type,
    e.event_ts,
    e.visitor_id,
    s.web_session_id,
    e.session_id,
    e.page_path,
    j.job_id,
    coalesce(j.organization_id, o.organization_id) as organization_id,
    json_strip_nulls(
        json_object(
            "outbound_url",
            e.outbound_url,
            "link_text",
            e.link_text,
            "click_method",
            e.click_method
        )
    ) as event_details
from {{ ref("stg_posthog__events") }} as e
left join {{ ref("dim_web_sessions") }} as s on e.session_id = s.source_session_id
left join
    {{ ref("dim_jobs") }} as j
    on e.organization_slug = j.organization_slug
    and e.job_slug = j.job_slug
left join
    {{ ref("dim_organizations") }} as o on e.organization_slug = o.organization_slug
where e.event_type in ("apply_click", "page_view")
