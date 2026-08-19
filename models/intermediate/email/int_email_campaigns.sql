with
    campaigns as (
        select
            email_campaign_id,
            source,
            subject,
            campaign_date,
            min(sent_ts) as first_sent_ts,
            max(sent_ts) as last_sent_ts,
            count(*) as message_count
        from {{ ref("int_email_messages") }}
        group by 1, 2, 3, 4
    ),
    campaign_names as (
        select
            m.email_campaign_id,
            any_value(
                regexp_extract(e.link_url, r"[?&]utm_campaign=([^&]+)")
            ) as campaign_name
        from {{ ref("int_email_message_events") }} as e
        left join {{ ref("int_email_messages") }} as m on e.email_id = m.email_id
        where regexp_contains(e.link_url, r"[?&]utm_campaign=")
        group by 1
    )

select
    c.email_campaign_id,
    c.source,
    n.campaign_name,
    c.subject,
    c.campaign_date,
    c.first_sent_ts,
    c.last_sent_ts,
    c.message_count,
    coalesce(starts_with(c.subject, "[TEST]"), false) as is_test
from campaigns as c
left join campaign_names as n on c.email_campaign_id = n.email_campaign_id
