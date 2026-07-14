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
    )

select
    subscriber_id,
    email_address,
    resend_contact_id,
    case
        when resend_contact_id is null
        then false
        when max_unsubscribed_ts is null
        then true
        else max_subscribed_ts > max_unsubscribed_ts
    end as is_subscribed,
    min_subscribed_ts,
    max_subscribed_ts,
    min_unsubscribed_ts,
    max_unsubscribed_ts
from subscription_summary
