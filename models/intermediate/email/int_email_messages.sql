with
    messages as (
        select
            email_id,
            source,
            source_email_id,
            any_value(subject) as subject,
            any_value(link_utm_campaign) as campaign_name,
            min(if(event_type = "sent", event_ts, null)) as first_sent_ts,
            min(event_ts) as first_event_ts
        from {{ ref("int_email_message_events") }}
        group by 1, 2, 3
    )

select
    email_id,
    {{
        dbt_utils.generate_surrogate_key(
            ["source", "subject", "date(coalesce(first_sent_ts, first_event_ts))"]
        )
    }} as email_campaign_id,
    source,
    source_email_id,
    subject,
    campaign_name,
    first_sent_ts,
    first_event_ts
from messages
