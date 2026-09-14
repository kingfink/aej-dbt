select
    u.url_impression_id,
    u.date_day,
    u.canonical_path,
    u.page_type,
    j.job_id,
    coalesce(j.organization_id, o.organization_id) as organization_id,
    u.query,
    u.is_anonymized_query,
    u.country,
    u.device,
    u.search_type,
    u.search_appearance,
    u.n_impressions,
    u.n_clicks,
    u.sum_position
from {{ ref("stg_google_search_console__url_impressions") }} as u
left join
    {{ ref("dim_jobs") }} as j
    on u.organization_slug = j.organization_slug
    and u.job_slug = j.job_slug
left join
    {{ ref("dim_organizations") }} as o on u.organization_slug = o.organization_slug
