select
    m.email_campaign_id,
    m.source,
    any_value(regexp_extract(e.link_url, r"[?&]utm_campaign=([^&]+)")) as campaign_name,
    m.subject,
    m.campaign_date,
    min(m.sent_ts) as first_sent_ts,
    max(m.sent_ts) as last_sent_ts,
    count(distinct m.email_id) as message_count,
    coalesce(starts_with(m.subject, "[TEST]"), false) as is_test
from {{ ref("int_email_messages") }} as m
left join {{ ref("int_email_message_events") }} as e on m.email_id = e.email_id
group by m.email_campaign_id, m.source, m.subject, m.campaign_date
