select
    organization_slug,
    is_active,
    is_featured,
    name,
    description,
    description_short,
    organization_url,
    headcount,
    location
from {{ ref("stg_organizations") }}
