select
    {{ dbt_utils.generate_surrogate_key(["email_id", "subscriber_id"]) }}
    as email_subscriber_message_id,
    email_id,
    subscriber_id,
    min(if(event_type = "sent", event_ts, null)) as min_sent_ts,
    min(if(event_type = "delivered", event_ts, null)) as min_delivered_ts,
    min(if(event_type = "opened", event_ts, null)) as min_opened_ts,
    min(if(event_type = "clicked", event_ts, null)) as min_clicked_ts,
    countif(event_type = "opened") as n_events_opened,
    countif(event_type = "clicked") as n_events_clicked
from {{ ref("fct_email_events") }}
where subscriber_id is not null
group by email_id, subscriber_id
