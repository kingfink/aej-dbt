select
    {{
        dbt_utils.generate_surrogate_key(
            [
                "e.email_id",
                normalize_email_address("r"),
            ]
        )
    }} as email_event_id,
    e.email_id as message_id,
    {{ normalize_email_address("r") }} as email_address,
    nullif(e.subject, "") as subject,
    e.created_at as email_created_ts
from {{ source("resend", "resend_emails_backfill") }} as e
cross join unnest(e.to_addresses) as r
where r is not null
