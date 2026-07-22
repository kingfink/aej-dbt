select
    {{ dbt_utils.generate_surrogate_key(["'netlify'", "submission_id"]) }}
    as form_submission_id,
    submission_id as source_form_submission_id,
    'netlify' as source,
    lower(trim(form_name)) as form_name,
    {{ normalize_email_address("json_value(form_data, '$.email')") }} as email_address,
    nullif(json_value(form_data, '$.job_slug'), '') as job_slug,
    nullif(json_value(form_data, '$.org_slug'), '') as organization_slug,
    nullif(json_value(form_data, '$.posthog_distinct_id'), '') as posthog_distinct_id,
    nullif(json_value(form_data, '$.posthog_session_id'), '') as posthog_session_id,
    json_strip_nulls(
        json_object(
            'job_title',
            nullif(json_value(form_data, '$.job_title'), ''),
            'job_url',
            nullif(json_value(form_data, '$.job_url'), '')
        )
    ) as form_submission_details,
    submitted_ts,
    loaded_ts
from {{ source("netlify", "form_submissions") }}
where submission_id is not null
