select
    broadcast_id,
    nullif(subject, "") as subject,
    nullif(html, "") as html,
    nullif(text, "") as text,
    status,
    created_at as broadcast_created_ts,
    scheduled_at as broadcast_scheduled_ts,
    sent_at as broadcast_sent_ts
from {{ source("resend_broadcasts", "broadcasts") }}
