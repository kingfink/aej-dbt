select
    {{ dbt_utils.generate_surrogate_key(["'posthog'", "e.session_id"]) }} as session_id,
    e.session_id as source_session_id,
    "posthog" as source,
    any_value(e.visitor_id) as visitor_id,
    min(e.event_ts) as session_started_ts,
    any_value(e.session_page_path) as session_page_path,
    any_value(e.session_referring_domain) as session_referring_domain,
    any_value(e.session_utm_source) as session_utm_source,
    any_value(e.session_utm_medium) as session_utm_medium,
    any_value(e.session_utm_campaign) as session_utm_campaign,
    any_value(e.browser) as browser,
    any_value(e.device_type) as device_type,
    any_value(e.country_code) as country_code,
    countif(e.event_type = "page_view") as page_view_count,
    count(
        distinct if(e.event_type = "page_view", e.page_path, null)
    ) as distinct_page_count,
    countif(e.event_type = "apply_click") as apply_click_count
from {{ ref("stg_posthog__events") }} as e
where e.session_id is not null
group by e.session_id
