-- Property-level impressions count one appearance per search even when several of
-- the site's pages rank for it, so property totals should never exceed URL totals
-- for the same date, and both exports should cover the same dates. A violation
-- means one of the two exports loaded partially.
with
    url_daily as (
        select date_day, sum(n_impressions) as n_impressions, sum(n_clicks) as n_clicks
        from {{ ref("fct_search_performance_daily") }}
        group by 1
    ),

    site_daily as (
        select date_day, sum(n_impressions) as n_impressions, sum(n_clicks) as n_clicks
        from {{ ref("fct_search_performance_site_daily") }}
        group by 1
    )

select
    coalesce(u.date_day, s.date_day) as date_day,
    u.n_impressions as url_impressions,
    s.n_impressions as site_impressions,
    u.n_clicks as url_clicks,
    s.n_clicks as site_clicks
from url_daily as u
full join site_daily as s on u.date_day = s.date_day
where
    u.date_day is null
    or s.date_day is null
    or s.n_impressions > u.n_impressions
    or s.n_clicks > u.n_clicks
