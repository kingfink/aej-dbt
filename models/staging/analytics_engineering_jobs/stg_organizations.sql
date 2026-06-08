select
    {{ get_organization_slug(file_path) }} as organization_slug,
    {{ get_frontmatter_value("frontmatter", "$.active", "bool") }} as is_active,
    {{ get_frontmatter_value("frontmatter", "$.featured", "bool") }} as is_featured,
    {{ get_frontmatter_value("frontmatter", "$.title", "string") }} as name,
    {{ get_frontmatter_value("frontmatter", "$.about", "string") }} as description,
    {{ get_frontmatter_value("frontmatter", "$.about_short", "string") }}
    as description_short,
    {{ get_frontmatter_value("frontmatter", "$.website", "string") }}
    as organization_url,
    coalesce(
        {{ get_frontmatter_value("frontmatter", "$.headcount", "string") }},
        {{ get_frontmatter_value("frontmatter", "$.headcount_inferred", "string") }}
    ) as headcount,
    coalesce(
        {{ get_frontmatter_value("frontmatter", "$.location", "string") }},
        {{ get_frontmatter_value("frontmatter", "$.location_inferred", "string") }}
    ) as location
from {{ source("analytics_engineering_jobs", "organizations") }}
