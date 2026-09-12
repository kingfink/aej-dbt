select distinct
    canonical_path,
    case
        when canonical_path = "/"
        then "home"
        when canonical_path = "/jobs/"
        then "job_index"
        when regexp_contains(canonical_path, r"^/jobs/[^/]+/[^/]+/$")
        then "job_detail"
        when canonical_path = "/organizations/"
        then "organization_index"
        when regexp_contains(canonical_path, r"^/organizations/[^/]+/$")
        then "organization"
        when regexp_contains(canonical_path, r"^/landing-pages/[^/]+/$")
        then "landing_page"
        when regexp_contains(canonical_path, r"^/tags/")
        then "tag"
        when canonical_path = "/subscribe/"
        then "subscribe"
        else "other"
    end as page_type,
    coalesce(
        regexp_extract(canonical_path, r"^/jobs/([^/]+)/[^/]+/$"),
        regexp_extract(canonical_path, r"^/organizations/([^/]+)/$")
    ) as organization_slug,
    regexp_extract(canonical_path, r"^/jobs/[^/]+/([^/]+)/$") as job_slug
from {{ ref("stg_search_console__url_impressions") }}
