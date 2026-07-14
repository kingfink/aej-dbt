with
    message_events as (
        select
            event_id as email_event_id,
            "sendgrid" as source,
            event_type,
            event_ts,
            message_id as source_email_id,
            email_address,
            cast(null as string) as subject,
            link_url,
            ip_address,
            user_agent,
            false as is_backfill
        from {{ ref("stg_sendgrid__email_events") }}

        union all

        select
            email_event_id,
            "resend" as source,
            event_type,
            case
                when event_type = "clicked"
                then coalesce(click_ts, event_created_ts)
                else event_created_ts
            end as event_ts,
            message_id as source_email_id,
            email_address,
            subject,
            click_link as link_url,
            click_ip_address as ip_address,
            click_user_agent as user_agent,
            false as is_backfill
        from {{ ref("stg_resend__email_events") }}

        union all

        select
            b.email_event_id,
            "resend" as source,
            "sent" as event_type,
            b.email_created_ts as event_ts,
            b.message_id as source_email_id,
            b.email_address,
            b.subject,
            cast(null as string) as link_url,
            cast(null as string) as ip_address,
            cast(null as string) as user_agent,
            true as is_backfill
        from {{ ref("stg_resend__emails_backfill") }} as b
        where
            not exists (
                select 1
                from {{ ref("stg_resend__email_events") }} as w
                where
                    w.message_id = b.message_id
                    and w.email_address = b.email_address
                    and w.event_type = "sent"
            )
    )

select
    email_event_id,
    {{ dbt_utils.generate_surrogate_key(["email_address"]) }} as subscriber_id,
    {{ dbt_utils.generate_surrogate_key(["source", "source_email_id"]) }} as email_id,
    source,
    event_type,
    event_ts,
    source_email_id,
    email_address,
    subject,
    link_url,
    ip_address,
    user_agent,
    is_backfill,
    {{ email_event_privacy_or_bot_reason("event_type", "user_agent") }}
    as privacy_or_bot_reason
from message_events
