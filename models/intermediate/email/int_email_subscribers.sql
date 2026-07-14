with
    subscription_summary as (
        select
            {{ dbt_utils.generate_surrogate_key(["email_address"]) }} as subscriber_id,
            email_address,
            any_value(resend_contact_id) as resend_contact_id,
            min(
                if(subscriber_event_type = "subscribed", event_ts, null)
            ) as min_subscribed_ts,
            max(
                if(subscriber_event_type = "subscribed", event_ts, null)
            ) as max_subscribed_ts,
            min(
                if(subscriber_event_type = "unsubscribed", event_ts, null)
            ) as min_unsubscribed_ts,
            max(
                if(subscriber_event_type = "unsubscribed", event_ts, null)
            ) as max_unsubscribed_ts
        from {{ ref("int_email_subscription_events") }}
        group by email_address
    ),
    current_resend_status as (
        select email_address, subscriber_event_type = "subscribed" as is_subscribed
        from {{ ref("int_email_subscription_events") }}
        where source = "resend"
        qualify
            row_number() over (
                partition by email_address
                order by
                    event_ts desc,
                    is_backfill,
                    subscriber_event_type = "unsubscribed" desc
            )
            = 1
    )

select
    s.subscriber_id,
    s.email_address,
    s.resend_contact_id,
    coalesce(c.is_subscribed, false) as is_subscribed,
    s.min_subscribed_ts,
    s.max_subscribed_ts,
    s.min_unsubscribed_ts,
    s.max_unsubscribed_ts
from subscription_summary as s
left join current_resend_status as c on s.email_address = c.email_address
