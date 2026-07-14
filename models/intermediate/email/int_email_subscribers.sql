with
    subscription_summary as (
        select
            subscriber_id,
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
        group by subscriber_id, email_address
    ),

    subscriber_identities as (
        select subscriber_id, email_address
        from subscription_summary

        union all

        select subscriber_id, email_address
        from {{ ref("int_email_message_events") }}
    ),

    subscribers as (
        select distinct subscriber_id, email_address from subscriber_identities
    )

select
    s.subscriber_id,
    s.email_address,
    l.resend_contact_id,
    case
        when l.resend_contact_id is null
        then false
        when l.max_unsubscribed_ts is null
        then true
        else l.max_subscribed_ts > l.max_unsubscribed_ts
    end as is_subscribed,
    l.min_subscribed_ts,
    l.max_subscribed_ts,
    l.min_unsubscribed_ts,
    l.max_unsubscribed_ts
from subscribers as s
left join subscription_summary as l on s.subscriber_id = l.subscriber_id
