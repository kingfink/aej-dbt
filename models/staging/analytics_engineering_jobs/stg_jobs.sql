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
            {{ get_frontmatter_value("frontmatter", "$.verified", "bool") }}
            as is_verified,
            json_value_array(frontmatter, '$.tags') as tags
        from {{ source("analytics_engineering_jobs", "jobs") }}
    ),
    salary_periods as (
        select
            organization_slug,
            job_slug,
            salary_min,
            salary_max,
            case
                coalesce(salary_unit, salary_unit_inferred)
                when 'HOUR'
                then 2080
                when 'DAY'
                then 260
                when 'WEEK'
                then 52
                when 'MONTH'
                then 12
                when 'YEAR'
                then 1
            end as annual_factor
        from frontmatter
        where is_verified is distinct from false
    ),
    annual_salaries as (
        select
            organization_slug,
            job_slug,
            safe_cast(
                safe_multiply(salary_min, annual_factor) as int64
            ) as salary_annual_min,
            safe_cast(
                safe_multiply(salary_max, annual_factor) as int64
            ) as salary_annual_max
        from salary_periods
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
    j.is_verified,
    s.salary_annual_min is not null
    and s.salary_annual_max is not null as is_salary_eligible,
    if(s.salary_annual_max is not null, s.salary_annual_min, null) as salary_annual_min,
    if(s.salary_annual_min is not null, s.salary_annual_max, null) as salary_annual_max,
    s.salary_annual_min / 2 + s.salary_annual_max / 2 as salary_annual_midpoint,
    (
        select if(count(distinct tag) = 1, any_value(tag), 'Unspecified')
        from unnest(j.tags) as tag
        where
            tag in (
                'Contract',
                'Internship',
                'Junior',
                'Lead',
                'Mid-Level',
                'Senior',
                'Staff'
            )
    ) as job_level,
    if('Remote' in unnest(j.tags), 'Remote', 'Other/unspecified') as remote_group
from frontmatter as j
left join
    annual_salaries as s
    on j.organization_slug = s.organization_slug
    and j.job_slug = s.job_slug
