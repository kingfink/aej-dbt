with
    subscriber_lifetimes as (
        select
            s.subscriber_id, s.email_address, min(date(e.event_ts)) as first_event_date
        from {{ ref("int_email_subscription_events") }} as e
        left join
            {{ ref("int_email_subscribers") }} as s on e.email_address = s.email_address
        group by s.subscriber_id, s.email_address
    ),
    subscriber_dates as (
        select date_day, s.subscriber_id, s.email_address
        from subscriber_lifetimes as s
        cross join
            unnest(generate_date_array(s.first_event_date, current_date())) as date_day
    ),
    ranked_status as (
        select
            d.date_day,
            d.subscriber_id,
            e.subscriber_event_type = "subscribed" as is_subscribed,
            row_number() over (
                partition by d.date_day, d.subscriber_id
                order by e.event_ts desc, e.subscriber_event_type = "unsubscribed" desc
            ) as status_event_rank
        from subscriber_dates as d
        left join
            {{ ref("int_email_subscription_events") }} as e
            on d.email_address = e.email_address
            and e.source = "resend"
            and date(e.event_ts) <= d.date_day
    )

select
    {{ dbt_utils.generate_surrogate_key(["date_day", "subscriber_id"]) }}
    as email_subscriber_daily_id,
    date_day,
    subscriber_id,
    coalesce(is_subscribed, false) as is_subscribed
from ranked_status
where status_event_rank = 1
