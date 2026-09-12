select
    {{ dbt_utils.generate_surrogate_key(["'posthog'", "uuid"]) }} as event_id,
    uuid as source_event_id,
    "posthog" as source,
    case
        event
        when "$pageview"
        then "page_view"
        when "$pageleave"
        then "page_leave"
        else ltrim(event, "$")
    end as event_type,
    timestamp as event_ts,
    distinct_id as visitor_id,
    json_value(properties, '$."$session_id"') as session_id,
    json_value(properties, '$."$pathname"') as page_path,
    coalesce(
        nullif(json_value(properties, "$.org_slug"), ""),
        regexp_extract(
            json_value(properties, '$."$pathname"'), r"^/jobs/([^/]+)/[^/]+/?$"
        )
    ) as organization_slug,
    coalesce(
        nullif(json_value(properties, "$.job_slug"), ""),
        regexp_extract(
            json_value(properties, '$."$pathname"'), r"^/jobs/[^/]+/([^/]+)/?$"
        )
    ) as job_slug,
    nullif(json_value(properties, "$.url"), "") as outbound_url,
    nullif(json_value(properties, "$.link_text"), "") as link_text,
    nullif(json_value(properties, "$.click_method"), "") as click_method,
    nullif(
        json_value(properties, '$."$session_entry_referrer"'), ""
    ) as session_entry_referrer,
    nullif(
        json_value(properties, '$."$session_entry_referring_domain"'), ""
    ) as session_entry_referring_domain,
    nullif(
        json_value(properties, '$."$session_entry_pathname"'), ""
    ) as session_entry_page_path,
    nullif(
        json_value(properties, '$."$session_entry_utm_source"'), ""
    ) as session_entry_utm_source,
    nullif(
        json_value(properties, '$."$session_entry_utm_medium"'), ""
    ) as session_entry_utm_medium,
    nullif(
        json_value(properties, '$."$session_entry_utm_campaign"'), ""
    ) as session_entry_utm_campaign,
    bq_ingested_timestamp as loaded_ts
from {{ source("posthog", "events") }}
where
    event is not null
    and json_value(properties, '$."$host"')
    in ("analyticsengineeringjobs.com", "www.analyticsengineeringjobs.com")
qualify row_number() over (partition by uuid order by bq_ingested_timestamp desc) = 1
