with
    frontmatter as (
        select
            {{ get_organization_slug("file_path") }} as organization_slug,
            {{ get_job_slug("file_path") }} as job_slug,
            {{ get_frontmatter_value("frontmatter", "$.active", "bool") }} as is_active,
            {{ get_frontmatter_value("frontmatter", "$.featured", "bool") }}
            as is_featured,
            {{ get_frontmatter_value("frontmatter", "$.date", "date") }} as date_added,
            {{ get_frontmatter_value("frontmatter", "$.closed_at", "date") }}
            as date_removed,
            {{ get_frontmatter_value("frontmatter", "$.title", "string") }} as title,
            {{ get_frontmatter_value("frontmatter", "$.url", "string") }}
            as posting_url,
            {{ get_frontmatter_value("frontmatter", "$.description", "string") }}
            as description,
            {{ get_frontmatter_value("frontmatter", "$.location", "string") }}
            as location,
            {{ get_frontmatter_value("frontmatter", "$.salary", "string") }} as salary,
            {{ get_frontmatter_value("frontmatter", "$.salary_min", "float64") }}
            as salary_min,
            {{ get_frontmatter_value("frontmatter", "$.salary_max", "float64") }}
            as salary_max,
            {{ get_frontmatter_value("frontmatter", "$.salary_unit") }} as salary_unit,
            {{ get_frontmatter_value("frontmatter", "$.salary_unit_inferred") }}
            as salary_unit_inferred,
            {{ get_frontmatter_value("frontmatter", "$.salary_source") }}
            as salary_source,
            json_value_array(frontmatter, '$.tags') as tags
        from {{ source("analytics_engineering_jobs", "jobs") }}
    )
select
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
    {{
        annualize_salary(
            "j.salary_min", "coalesce(j.salary_unit, j.salary_unit_inferred)"
        )
    }} as salary_annual_min,
    {{
        annualize_salary(
            "j.salary_max", "coalesce(j.salary_unit, j.salary_unit_inferred)"
        )
    }} as salary_annual_max,
    'Remote' in unnest(j.tags) as is_remote
from frontmatter as j
