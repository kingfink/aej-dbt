select
    sg_event_id as event_id,
    sg_message_id as message_id,
    {{ normalize_email_address("email") }} as email_address,
    {{ normalize_event_type("event") }} as event_type,
    timestamp_seconds(timestamp) as event_ts,
    nullif(url, "") as link_url,
    nullif(ip, "") as ip_address,
    nullif(useragent, "") as user_agent
from {{ source("sendgrid", "webhooks") }}
where email is not null and event is not null
