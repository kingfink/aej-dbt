select
    {{
        dbt_utils.generate_surrogate_key(
            [
                "data_date",
                "query",
                "is_anonymized_query",
                "country",
                "lower(search_type)",
                "lower(device)",
            ]
        )
    }} as site_impression_id,
    data_date as date_day,
    query,
    is_anonymized_query,
    country,
    lower(search_type) as search_type,
    lower(device) as device,
    sum(impressions) as impressions,
    sum(clicks) as clicks,
    sum(sum_top_position) as sum_top_position
from {{ source("google_search_console", "searchdata_site_impression") }}
group by 1, 2, 3, 4, 5, 6, 7
