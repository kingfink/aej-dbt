select
    {{ normalize_event_type("event_type") }} as event_type,
    event_created_at as event_created_ts,
    contact_id,
    {{ normalize_email_address("email") }} as email_address,
    not unsubscribed as is_subscribed
from {{ source("resend", "resend_wh_contacts") }}
where email is not null
