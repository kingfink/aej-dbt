select
    site_impression_id,
    data_date,
    query,
    is_anonymized_query,
    country,
    device,
    search_type,
    impressions,
    clicks,
    sum_top_position
from {{ ref("stg_search_console__site_impressions") }}
