with
    sessions as (
        select
            session_id as source_session_id,
            any_value(visitor_id) as visitor_id,
            min(event_ts) as session_started_ts,
            any_value(session_page_path) as session_page_path,
            any_value(session_referring_domain) as session_referring_domain,
            any_value(session_utm_source) as session_utm_source,
            any_value(session_utm_medium) as session_utm_medium,
            any_value(session_utm_campaign) as session_utm_campaign
        from {{ ref("stg_posthog__events") }}
        where session_id is not null
        group by 1
    )

select
    {{ dbt_utils.generate_surrogate_key(["'posthog'", "source_session_id"]) }}
    as session_id,
    source_session_id,
    "posthog" as source,
    visitor_id,
    session_started_ts,
    session_page_path,
    session_referring_domain,
    session_utm_source,
    session_utm_medium,
    session_utm_campaign,
    case
        when session_utm_medium = "email" or session_utm_source = "newsletter"
        then "email"
        when session_utm_medium in ("paid", "cpc", "ppc")
        then "paid"
        when session_utm_medium = "organic"
        then "organic_search"
        when session_utm_medium = "referral"
        then "referral"
        when session_referring_domain = "$direct"
        then "direct"
        when
            session_referring_domain
            in ("analyticsengineeringjobs.com", "www.analyticsengineeringjobs.com")
        then "internal"
        when
            session_referring_domain in (
                "chatgpt.com",
                "chat.openai.com",
                "claude.ai",
                "copilot.microsoft.com",
                "gemini.google.com",
                "grok.com",
                "meta.ai",
                "perplexity.ai",
                "www.perplexity.ai"
            )
        then "ai_assistant"
        when
            regexp_contains(
                session_referring_domain,
                r"^(www\.|m\.|search\.|r\.search\.|lite\.|html\.)?(google|bing|duckduckgo|yahoo|ecosia|brave|yandex|baidu|startpage|qwant|naver|seznam|mojeek)\."
            )
        then "organic_search"
        when
            session_referring_domain in (
                "com.google.android.gm",
                "e.mail.ru",
                "mail.aol.com",
                "mail.google.com",
                "mail.proton.me",
                "mail.yahoo.com",
                "mail.zoho.com",
                "outlook.live.com",
                "outlook.office.com",
                "outlook.office365.com",
                "superhuman.com"
            )
        then "email"
        else "referral"
    end as channel
from sessions
