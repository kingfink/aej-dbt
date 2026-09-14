-- Shared site path macros, checked against literal cases. Any row returned is a
-- case where a macro disagrees with the expected value.
with
    cases as (
        select *
        from
            unnest(
                [
                    struct(
                        "https://www.analyticsengineeringjobs.com/jobs/zocdoc/staff-analytics-engineer-2/?utm_source=google#apply"
                        as url_or_path,
                        "/jobs/zocdoc/staff-analytics-engineer-2/" as expected_path,
                        "job" as expected_page_type,
                        "zocdoc" as expected_organization_slug,
                        "staff-analytics-engineer-2" as expected_job_slug
                    ),
                    ("https://analyticsengineeringjobs.com", "/", "home", null, null),
                    ("/jobs", "/jobs/", "job_index", null, null),
                    (
                        "/jobs/airbnb-senior-analytics-engineer/",
                        "/jobs/airbnb-senior-analytics-engineer/",
                        "job",
                        "airbnb-senior-analytics-engineer",
                        null
                    ),
                    (
                        "/organizations/",
                        "/organizations/",
                        "organization_index",
                        null,
                        null
                    ),
                    (
                        "https://analyticsengineeringjobs.com/organizations/zocdoc",
                        "/organizations/zocdoc/",
                        "organization",
                        "zocdoc",
                        null
                    ),
                    (
                        "/landing-pages/dbt/?q=",
                        "/landing-pages/dbt/",
                        "landing_page",
                        "dbt",
                        null
                    ),
                    ("/tags/", "/tags/", "tag", null, null),
                    ("/subscribe/", "/subscribe/", "subscribe", null, null),
                    ("/about/", "/about/", "other", null, null)
                ]
            )
    ),

    parsed as (
        select
            *,
            {{ normalize_page_path("url_or_path") }} as actual_path,
            {{ get_page_type(normalize_page_path("url_or_path")) }} as actual_page_type,
            {{ get_organization_slug(normalize_page_path("url_or_path")) }}
            as actual_organization_slug,
            {{ get_job_slug(normalize_page_path("url_or_path")) }} as actual_job_slug
        from cases
    )

select *
from parsed
where
    actual_path is distinct from expected_path
    or actual_page_type is distinct from expected_page_type
    or actual_organization_slug is distinct from expected_organization_slug
    or actual_job_slug is distinct from expected_job_slug
