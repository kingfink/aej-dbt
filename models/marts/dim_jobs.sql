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
    j.salary_min,
    j.salary_max,
    j.salary_unit,
    j.salary_unit_inferred,
    j.salary_source,
    j.is_salary_eligible,
    j.salary_annual_min,
    j.salary_annual_max,
    j.salary_annual_midpoint,
    j.job_level,
    j.remote_group
from {{ ref("stg_jobs") }} as j
left join
    {{ ref("dim_organizations") }} as o on j.organization_slug = o.organization_slug
