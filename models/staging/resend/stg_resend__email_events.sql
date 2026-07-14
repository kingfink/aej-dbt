select
    {{
        dbt_utils.generate_surrogate_key(
            [
                "e.id",
                normalize_email_address("r"),
            ]
        )
    }} as email_event_id,
    {{ normalize_event_type("e.event_type") }} as event_type,
    e.event_created_at as event_created_ts,
    e.email_id as message_id,
    {{ normalize_email_address("r") }} as email_address,
    nullif(e.subject, "") as subject,
    nullif(e.click_ip_address, "") as click_ip_address,
    nullif(e.click_link, "") as click_link,
    e.click_timestamp as click_ts,
    nullif(e.click_user_agent, "") as click_user_agent
from {{ source("resend", "resend_wh_emails") }} as e
cross join unnest(e.to_addresses) as r
where r is not null
