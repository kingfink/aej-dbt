select
    {{ dbt_utils.generate_surrogate_key(["j.organization_slug", "j.job_slug"]) }}
    as job_id,
    o.organization_id,
    j.organization_slug,
    j.job_slug,
    j.is_active,
    j.is_featured,
    j.date_added,
    j.date_removed,
    j.title,
    j.posting_url,
    j.description,
    j.location,
    j.salary,
    j.tags
from {{ ref("stg_jobs") }} as j
left join
    {{ ref("dim_organizations") }} as o on j.organization_slug = o.organization_slug
