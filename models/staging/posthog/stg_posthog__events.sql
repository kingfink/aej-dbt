{%- set pathname = "nullif(json_value(properties, '$.\"$pathname\"'), '')" -%}
{%- set session_pathname = (
    "nullif(json_value(properties, '$.\"$session_entry_pathname\"'), '')"
) -%}

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
    {{ normalize_page_path(pathname) }} as page_path,
    coalesce(
        nullif(json_value(properties, "$.org_slug"), ""),
        {{ get_organization_slug(normalize_page_path(pathname)) }}
    ) as organization_slug,
    coalesce(
        nullif(json_value(properties, "$.job_slug"), ""),
        {{ get_job_slug(normalize_page_path(pathname)) }}
    ) as job_slug,
    nullif(json_value(properties, "$.url"), "") as outbound_url,
    nullif(json_value(properties, "$.link_text"), "") as link_text,
    nullif(json_value(properties, "$.click_method"), "") as click_method,
    nullif(
        json_value(properties, '$."$session_entry_referrer"'), ""
    ) as session_referrer,
    nullif(
        json_value(properties, '$."$session_entry_referring_domain"'), ""
    ) as session_referring_domain,
    {{ normalize_page_path(session_pathname) }} as session_page_path,
    lower(
        nullif(json_value(properties, '$."$session_entry_utm_source"'), "")
    ) as session_utm_source,
    lower(
        nullif(json_value(properties, '$."$session_entry_utm_medium"'), "")
    ) as session_utm_medium,
    nullif(
        json_value(properties, '$."$session_entry_utm_campaign"'), ""
    ) as session_utm_campaign,
    bq_ingested_timestamp as loaded_ts
from {{ source("posthog", "events") }}
where
    event is not null
    and json_value(properties, '$."$host"')
    in ("analyticsengineeringjobs.com", "www.analyticsengineeringjobs.com")
qualify
    row_number() over (partition by timestamp, uuid order by bq_ingested_timestamp desc)
    = 1
