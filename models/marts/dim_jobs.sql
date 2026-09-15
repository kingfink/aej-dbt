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
    j.tags,
    j.salary_annual_min,
    j.salary_annual_max,
    (j.salary_annual_min + j.salary_annual_max) / 2 as salary_annual_midpoint,
    j.is_remote,
    j.level,
    j.role_type
from {{ ref("stg_jobs") }} as j
left join
    {{ ref("dim_organizations") }} as o on j.organization_slug = o.organization_slug
