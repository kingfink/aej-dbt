with
    pages as (
        select distinct
            canonical_path,
            case
                when canonical_path = "/"
                then "home"
                when canonical_path = "/jobs/"
                then "job_index"
                when canonical_path like "/jobs/%"
                then "job_detail"
                when canonical_path = "/organizations/"
                then "organization_index"
                when canonical_path like "/organizations/%"
                then "organization"
                when canonical_path like "/landing-pages/%"
                then "landing_page"
                when canonical_path like "/tags/%"
                then "tag"
                when canonical_path = "/subscribe/"
                then "subscribe"
                else "other"
            end as page_type,
            {{ get_organization_slug("canonical_path") }} as path_organization_slug,
            nullif({{ get_job_slug("canonical_path") }}, "") as path_job_slug
        from {{ ref("stg_google_search_console__url_impressions") }}
    )

select
    canonical_path,
    page_type,
    case
        when page_type = "organization"
        then path_organization_slug
        when page_type = "job_detail" and path_job_slug is not null
        then path_organization_slug
    end as organization_slug,
    if(page_type = "job_detail", path_job_slug, null) as job_slug
from pages
