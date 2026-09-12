select
    u.url_impression_id,
    u.data_date,
    u.canonical_path,
    p.page_type,
    j.job_id,
    coalesce(j.organization_id, o.organization_id) as organization_id,
    u.query,
    u.is_anonymized_query,
    u.country,
    u.device,
    u.search_type,
    u.is_job_listing,
    u.is_job_details,
    u.impressions,
    u.clicks,
    u.sum_position
from {{ ref("stg_search_console__url_impressions") }} as u
left join
    {{ ref("int_search_console__pages") }} as p on u.canonical_path = p.canonical_path
left join
    {{ ref("dim_jobs") }} as j
    on p.organization_slug = j.organization_slug
    and p.job_slug = j.job_slug
left join
    {{ ref("dim_organizations") }} as o on p.organization_slug = o.organization_slug
