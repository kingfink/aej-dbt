select
    subscriber_id,
    email_address,
    resend_contact_id,
    is_subscribed,
    min_subscribed_ts,
    max_subscribed_ts,
    min_unsubscribed_ts,
    max_unsubscribed_ts
from {{ ref("int_email_subscribers") }}
