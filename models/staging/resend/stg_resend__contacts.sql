select
    contact_id,
    {{ normalize_email_address("email") }} as email_address,
    not unsubscribed as is_subscribed,
    created_at as contact_created_ts,
    backfilled_at as backfilled_ts
from {{ source("resend", "resend_contacts_backfill") }}
where email is not null
