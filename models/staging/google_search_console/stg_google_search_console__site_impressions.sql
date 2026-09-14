select
    {{
        dbt_utils.generate_surrogate_key(
            [
                "data_date",
                "query",
                "upper(country)",
                "lower(search_type)",
                "lower(device)",
            ]
        )
    }} as site_impression_id,
    data_date as date_day,
    query,
    upper(country) as country_code,
    lower(search_type) as search_type,
    lower(device) as device,
    sum(impressions) as n_impressions,
    sum(clicks) as n_clicks,
    sum(sum_top_position) as sum_top_position
from {{ source("google_search_console", "searchdata_site_impression") }}
group by 1, 2, 3, 4, 5, 6
