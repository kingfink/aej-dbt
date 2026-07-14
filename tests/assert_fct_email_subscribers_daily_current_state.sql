select
    d.subscriber_id,
    d.is_subscribed as daily_is_subscribed,
    s.is_subscribed as current_is_subscribed
from {{ ref("fct_email_subscribers_daily") }} as d
left join {{ ref("dim_email_subscribers") }} as s on d.subscriber_id = s.subscriber_id
where d.date_day = current_date() and d.is_subscribed is distinct from s.is_subscribed
