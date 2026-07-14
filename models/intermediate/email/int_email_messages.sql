select
    email_id,
    source,
    source_email_id,
    any_value(subject) as subject,
    min(if(event_type = "sent", event_ts, null)) as sent_ts
from {{ ref("int_email_message_events") }}
group by 1, 2, 3
