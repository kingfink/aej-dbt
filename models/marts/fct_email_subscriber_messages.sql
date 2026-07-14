select
    {{ dbt_utils.generate_surrogate_key(["email_id", "subscriber_id"]) }}
    as email_subscriber_message_id,
    email_id,
    subscriber_id,
    min(if(event_type = "sent", event_ts, null)) as sent_ts,
    min(if(event_type = "delivered", event_ts, null)) as delivered_ts,
    min(if(event_type = "opened", event_ts, null)) as min_opened_ts,
    min(if(event_type = "clicked", event_ts, null)) as min_clicked_ts,
    countif(event_type = "opened") as open_event_count,
    countif(event_type = "clicked") as click_event_count,
    min(
        if(event_type = "opened" and not is_privacy_or_bot_like, event_ts, null)
    ) as min_non_privacy_or_bot_opened_ts,
    min(
        if(event_type = "clicked" and not is_privacy_or_bot_like, event_ts, null)
    ) as min_non_privacy_or_bot_clicked_ts
from {{ ref("fct_email_events") }}
group by email_id, subscriber_id
