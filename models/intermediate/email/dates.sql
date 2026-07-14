{{ config(materialized="ephemeral") }}

select date_day
from
    unnest(
        generate_date_array(
            (
                select min(date(event_ts))
                from {{ ref("int_email_subscription_events") }}
            ),
            current_date()
        )
    ) as date_day
