with
    link_clicks as (
        select
            email_event_id,
            email_id,
            email_address,
            event_ts as clicked_ts,
            privacy_or_bot_reason is not null as is_privacy_or_bot_like,
            regexp_replace(link_url, r"[?#].*$", "") as link_url,
            net.host(link_url) as link_host,
            regexp_extract(link_url, r"^https?://[^/?#]+([^?#]*)") as link_path
        from {{ ref("int_email_message_events") }}
        where event_type = "clicked" and link_url is not null
    ),
    classified_clicks as (
        select
            email_event_id,
            email_id,
            email_address,
            clicked_ts,
            is_privacy_or_bot_like,
            link_url,
            case
                when starts_with(link_host, "unsubscribe.")
                then "unsubscribe"
                when
                    link_host not in (
                        "analyticsengineeringjobs.com",
                        "www.analyticsengineeringjobs.com"
                    )
                then "external"
                when regexp_contains(link_path, r"^/jobs/[^/]+(/[^/]+)?/?$")
                then "job_page"
                else "site"
            end as link_type,
            regexp_extract(link_path, r"^/jobs/([^/]+)/[^/]+/?$") as organization_slug,
            regexp_extract(link_path, r"^/jobs/[^/]+/([^/]+)/?$") as job_slug
        from link_clicks
    )

select
    c.email_event_id,
    m.email_campaign_id,
    c.email_id,
    s.subscriber_id,
    c.link_url,
    c.link_type,
    j.job_id,
    coalesce(j.organization_id, o.organization_id) as organization_id,
    c.clicked_ts,
    c.is_privacy_or_bot_like
from classified_clicks as c
left join {{ ref("int_email_messages") }} as m on c.email_id = m.email_id
left join {{ ref("int_email_subscribers") }} as s on c.email_address = s.email_address
left join
    {{ ref("dim_jobs") }} as j
    on c.organization_slug = j.organization_slug
    and c.job_slug = j.job_slug
left join
    {{ ref("dim_organizations") }} as o on c.organization_slug = o.organization_slug
