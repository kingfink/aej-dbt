select
    {{ get_organization_slug(file_path) }} as organization_slug,
    {{ get_job_slug(file_path) }} as job_slug,
    {{ get_frontmatter_value("frontmatter", "$.active", "bool") }} as is_active,
    {{ get_frontmatter_value("frontmatter", "$.featured", "bool") }} as is_featured,
    {{ get_frontmatter_value("frontmatter", "$.date", "date") }} as date_added,
    {{ get_frontmatter_value("frontmatter", "$.closed_at", "date") }} as date_removed,
    {{ get_frontmatter_value("frontmatter", "$.title", "string") }} as title,
    {{ get_frontmatter_value("frontmatter", "$.url", "string") }} as posting_url,
    {{ get_frontmatter_value("frontmatter", "$.description", "string") }}
    as description,
    {{ get_frontmatter_value("frontmatter", "$.location", "string") }} as location,
    {{ get_frontmatter_value("frontmatter", "$.salary", "string") }} as salary,
    json_value_array(frontmatter, '$.tags') as tags
from {{ source("analytics_engineering_jobs", "jobs") }}
