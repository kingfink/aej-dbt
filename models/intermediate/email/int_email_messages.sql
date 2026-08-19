with
    messages as (
        select
            email_id,
            source,
            source_email_id,
            any_value(subject) as subject,
            min(if(event_type = "sent", event_ts, null)) as sent_ts,
            date(
                coalesce(min(if(event_type = "sent", event_ts, null)), min(event_ts))
            ) as campaign_date
        from {{ ref("int_email_message_events") }}
        group by 1, 2, 3
    )

select
    email_id,
    {{ dbt_utils.generate_surrogate_key(["source", "subject", "campaign_date"]) }}
    as email_campaign_id,
    source,
    source_email_id,
    subject,
    campaign_date,
    sent_ts
from messages
