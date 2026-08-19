select
    m.email_campaign_id,
    m.source,
    any_value(m.campaign_name) as campaign_name,
    m.subject,
    date(coalesce(m.first_sent_ts, m.first_event_ts)) as campaign_date,
    min(m.first_sent_ts) as first_sent_ts,
    count(*) as message_count,
    coalesce(starts_with(m.subject, "[TEST]"), false) as is_test
from {{ ref("int_email_messages") }} as m
group by m.email_campaign_id, m.source, m.subject, campaign_date
