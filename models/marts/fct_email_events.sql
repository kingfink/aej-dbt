with
    message_events as (
        select
            email_event_id,
            email_id,
            email_address,
            event_type,
            event_ts,
            ip_address,
            user_agent,
            is_backfill,
            privacy_or_bot_reason,
            if(event_type = "clicked", link_url, null) as clicked_url
        from {{ ref("int_email_message_events") }}
    )

select
    e.email_event_id,
    s.subscriber_id,
    e.email_id,
    e.event_type,
    e.event_ts,
    regexp_replace(e.clicked_url, r"[?#].*$", "") as link_url,
    case
        when e.clicked_url is null
        then null
        when starts_with(net.host(e.clicked_url), "unsubscribe.")
        then "unsubscribe"
        when
            net.host(e.clicked_url)
            not in ("analyticsengineeringjobs.com", "www.analyticsengineeringjobs.com")
        then "external"
        when
            regexp_contains(
                e.clicked_url, r"^https?://[^/?#]+/jobs/[^/?#]+(/[^/?#]+)?/?(?:[?#]|$)"
            )
        then "job_page"
        else "site"
    end as link_type,
    j.job_id,
    e.event_type in ("opened", "clicked") as is_engagement,
    e.privacy_or_bot_reason is not null as is_privacy_or_bot_like,
    json_strip_nulls(
        json_object(
            "ip_address",
            e.ip_address,
            "user_agent",
            e.user_agent,
            "is_backfill",
            e.is_backfill,
            "is_privacy_or_bot_like",
            e.privacy_or_bot_reason is not null,
            "privacy_or_bot_reason",
            e.privacy_or_bot_reason
        )
    ) as email_event_details
from message_events as e
left join {{ ref("int_email_subscribers") }} as s on e.email_address = s.email_address
left join
    {{ ref("dim_jobs") }} as j
    on regexp_extract(
        e.clicked_url, r"^https?://[^/?#]+/jobs/([^/?#]+)/[^/?#]+/?(?:[?#]|$)"
    )
    = j.organization_slug
    and regexp_extract(
        e.clicked_url, r"^https?://[^/?#]+/jobs/[^/?#]+/([^/?#]+)/?(?:[?#]|$)"
    )
    = j.job_slug
