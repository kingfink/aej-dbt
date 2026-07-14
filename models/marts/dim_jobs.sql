select
    organization_slug,
    job_slug,
    is_active,
    is_featured,
    date_added,
    date_removed,
    title,
    posting_url,
    description,
    location,
    salary,
    tags
from {{ ref("stg_jobs") }}
