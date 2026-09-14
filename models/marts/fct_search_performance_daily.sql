select
    u.url_impression_id,
    u.date_day,
    p.page_id,
    j.job_id,
    coalesce(j.organization_id, o.organization_id) as organization_id,
    c.country_id,
    u.query,
    u.device,
    u.search_type,
    u.search_appearance,
    u.n_impressions,
    u.n_clicks,
    u.sum_position
from {{ ref("stg_google_search_console__url_impressions") }} as u
left join {{ ref("dim_pages") }} as p on u.page_path = p.page_path
left join
    {{ ref("dim_jobs") }} as j
    on u.organization_slug = j.organization_slug
    and u.job_slug = j.job_slug
left join
    {{ ref("dim_organizations") }} as o on u.organization_slug = o.organization_slug
left join {{ ref("dim_countries") }} as c on u.country_code = c.alpha_3_code
