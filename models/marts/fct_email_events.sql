select
    e.email_event_id,
    s.subscriber_id,
    e.email_id,
    e.event_type,
    e.event_ts,
    json_strip_nulls(
        json_object(
            "link_url",
            e.link_url,
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
from {{ ref("int_email_message_events") }} as e
left join {{ ref("int_email_subscribers") }} as s on e.email_address = s.email_address
