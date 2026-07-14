select
    "resend" as source,
    contact_id as resend_contact_id,
    email_address,
    "subscribed" as subscriber_event_type,
    contact_created_ts as event_ts
from {{ ref("stg_resend__contacts") }}

union all

select
    "resend" as source,
    contact_id as resend_contact_id,
    email_address,
    "unsubscribed" as subscriber_event_type,
    backfilled_ts as event_ts
from {{ ref("stg_resend__contacts") }}
where not is_subscribed

union all

select
    "resend" as source,
    contact_id as resend_contact_id,
    email_address,
    if(is_subscribed, "subscribed", "unsubscribed") as subscriber_event_type,
    event_created_ts as event_ts
from {{ ref("stg_resend__contact_events") }}
where event_type in ("contact.created", "contact.updated")

union all

select
    "sendgrid" as source,
    cast(null as string) as resend_contact_id,
    email_address,
    "subscribed" as subscriber_event_type,
    event_ts
from {{ ref("int_email_message_events") }}
where source = "sendgrid" and event_type = "resubscribed"
