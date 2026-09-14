select
    s.site_impression_id,
    s.date_day,
    c.country_id,
    s.query,
    s.device,
    s.search_type,
    s.n_impressions,
    s.n_clicks,
    s.sum_top_position
from {{ ref("stg_google_search_console__site_impressions") }} as s
left join {{ ref("dim_countries") }} as c on s.country_code = c.alpha_3_code
