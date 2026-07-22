select
    {{ dbt_utils.generate_surrogate_key(["'webflow'", "event_id"]) }}
    as form_submission_id,
    event_id as source_form_submission_id,
    'webflow' as source,
    trim(regexp_replace(lower(trim(form_name)), r'[^a-z0-9]+', '-')) as form_name,
    {{ normalize_email_address("data") }} as email_address,
    cast(null as string) as job_slug,
    cast(null as string) as organization_slug,
    cast(null as string) as posthog_distinct_id,
    cast(null as string) as posthog_session_id,
    json '{}' as form_submission_details,
    event_timestamp as submitted_ts
from {{ source("webflow", "webhooks_form_submits") }}
where event_id is not null
