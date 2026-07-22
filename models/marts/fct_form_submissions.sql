with
    form_submissions as (
        select
            form_submission_id,
            source_form_submission_id,
            source,
            form_name,
            email_address,
            job_slug,
            organization_slug,
            posthog_distinct_id,
            posthog_session_id,
            form_submission_details,
            submitted_ts
        from {{ ref("stg_netlify__form_submissions") }}

        union all

        select
            form_submission_id,
            source_form_submission_id,
            source,
            form_name,
            email_address,
            job_slug,
            organization_slug,
            posthog_distinct_id,
            posthog_session_id,
            form_submission_details,
            submitted_ts
        from {{ ref("stg_webflow__form_submissions") }}
    )

select
    fs.form_submission_id,
    fs.source_form_submission_id,
    fs.source,
    fs.form_name,
    es.subscriber_id,
    j.job_id,
    coalesce(j.organization_id, o.organization_id) as organization_id,
    fs.email_address,
    fs.posthog_distinct_id,
    fs.posthog_session_id,
    fs.form_submission_details,
    fs.submitted_ts
from form_submissions as fs
left join
    {{ ref("dim_email_subscribers") }} as es on fs.email_address = es.email_address
left join
    {{ ref("dim_jobs") }} as j
    on fs.organization_slug = j.organization_slug
    and fs.job_slug = j.job_slug
left join
    {{ ref("dim_organizations") }} as o on fs.organization_slug = o.organization_slug
