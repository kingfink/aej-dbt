select
    site_impression_id,
    date_day,
    query,
    is_anonymized_query,
    country,
    device,
    search_type,
    impressions,
    clicks,
    sum_top_position
from {{ ref("stg_google_search_console__site_impressions") }}
