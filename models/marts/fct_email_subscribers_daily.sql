with
    subscriber_lifetimes as (
        select subscriber_id, min(date(event_ts)) as first_event_date
        from {{ ref("int_email_subscription_events") }}
        group by subscriber_id
    ),
    subscriber_dates as (
        select d.date_day, s.subscriber_id
        from subscriber_lifetimes as s
        left join {{ ref("dates") }} as d on d.date_day >= s.first_event_date
    ),
    daily_status as (
        select
            d.date_day,
            d.subscriber_id,
            countif(
                e.subscriber_event_type = "subscribed" and date(e.event_ts) = d.date_day
            )
            > 0 as subscribed_on_date,
            max(
                if(
                    e.subscriber_event_type = "subscribed"
                    and date(e.event_ts) < d.date_day,
                    e.event_ts,
                    null
                )
            ) as max_subscribed_ts_before_date,
            max(
                if(
                    e.subscriber_event_type = "unsubscribed"
                    and date(e.event_ts) < d.date_day,
                    e.event_ts,
                    null
                )
            ) as max_unsubscribed_ts_before_date
        from subscriber_dates as d
        left join
            {{ ref("int_email_subscription_events") }} as e
            on d.subscriber_id = e.subscriber_id
            and e.source = "resend"
            and date(e.event_ts) <= d.date_day
        group by d.date_day, d.subscriber_id
    )

select
    {{ dbt_utils.generate_surrogate_key(["date_day", "subscriber_id"]) }}
    as email_subscriber_daily_id,
    date_day,
    subscriber_id,
    subscribed_on_date
    or (
        max_subscribed_ts_before_date is not null
        and (
            max_unsubscribed_ts_before_date is null
            or max_subscribed_ts_before_date > max_unsubscribed_ts_before_date
        )
    ) as is_subscribed
from daily_status
