-- Extraction and repair validate these fields before writing frontmatter.
-- Fail the build if raw ingestion receives a partial or invalid observation.
select
    organization_slug,
    job_slug,
    salary_min,
    salary_max,
    salary_unit,
    salary_unit_inferred,
    salary_source
from {{ ref("stg_jobs") }}
where
    (salary_min is not null or salary_max is not null or salary_source is not null)
    and not coalesce(
        salary_min > 0
        and salary_max >= salary_min
        and not is_inf(salary_min)
        and not is_inf(salary_max)
        and salary_source in ('salary', 'description')
        and (
            salary_unit in ('HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR')
            or (
                salary_unit is null
                and salary_unit_inferred = 'YEAR'
                and salary_min >= 20000
            )
        ),
        false
    )
