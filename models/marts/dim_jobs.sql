with
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
        from {{ ref("stg_jobs") }}
        where
            is_verified is distinct from false
            and salary_source in ('salary', 'description')
            and salary_min > 0
            and salary_max >= salary_min
            and not is_inf(salary_min)
            and not is_inf(salary_max)
            and not is_nan(salary_min)
            and not is_nan(salary_max)
            and (
                salary_unit in ('HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR')
                or (
                    salary_unit is null
                    and salary_unit_inferred = 'YEAR'
                    and salary_min >= 20000
                )
            )
    ),
    annual_salaries as (
        select
            organization_slug,
            job_slug,
            round(safe_multiply(salary_min, annual_factor), 2) as salary_annual_min,
            round(safe_multiply(salary_max, annual_factor), 2) as salary_annual_max
        from salary_periods
    )
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
from {{ ref("stg_jobs") }} as j
left join
    {{ ref("dim_organizations") }} as o on j.organization_slug = o.organization_slug
left join
    annual_salaries as s
    on j.organization_slug = s.organization_slug
    and j.job_slug = s.job_slug
