select
    email_campaign_id,
    source,
    campaign_name,
    subject,
    campaign_date,
    first_sent_ts,
    last_sent_ts,
    message_count,
    is_test
from {{ ref("int_email_campaigns") }}
