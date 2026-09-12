-- Property-level impressions count one appearance per search even when several of
-- the site's pages rank for it, so property totals should never exceed URL totals
-- for the same date, and both exports should cover the same dates. A violation
-- means one of the two exports loaded partially.
with
    url_daily as (
        select data_date, sum(impressions) as impressions, sum(clicks) as clicks
        from {{ ref("fct_search_performance_daily") }}
        group by 1
    ),

    site_daily as (
        select data_date, sum(impressions) as impressions, sum(clicks) as clicks
        from {{ ref("fct_search_performance_site_daily") }}
        group by 1
    )

select
    coalesce(u.data_date, s.data_date) as data_date,
    u.impressions as url_impressions,
    s.impressions as site_impressions,
    u.clicks as url_clicks,
    s.clicks as site_clicks
from url_daily as u
full join site_daily as s on u.data_date = s.data_date
where
    u.data_date is null
    or s.data_date is null
    or s.impressions > u.impressions
    or s.clicks > u.clicks
