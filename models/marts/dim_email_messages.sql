select
    email_id,
    email_campaign_id,
    source,
    source_email_id,
    subject,
    first_sent_ts as sent_ts
from {{ ref("int_email_messages") }}
