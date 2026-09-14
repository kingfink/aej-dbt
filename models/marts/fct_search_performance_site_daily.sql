select
    site_impression_id,
    date_day,
    query,
    country,
    device,
    search_type,
    n_impressions,
    n_clicks,
    sum_top_position
from {{ ref("stg_google_search_console__site_impressions") }}
