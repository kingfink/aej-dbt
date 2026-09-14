with
    url_impressions as (
        select
            data_date as date_day,
            {{ normalize_page_path("url") }} as canonical_path,
            query,
            country,
            lower(search_type) as search_type,
            lower(device) as device,
            case
                when is_job_listing
                then "job_listing"
                when is_job_details
                then "job_details"
            end as search_appearance,
            impressions,
            clicks,
            sum_position
        from {{ source("google_search_console", "searchdata_url_impression") }}
    )

select
    {{
        dbt_utils.generate_surrogate_key(
            [
                "date_day",
                "canonical_path",
                "query",
                "country",
                "search_type",
                "device",
                "search_appearance",
            ]
        )
    }} as url_impression_id,
    date_day,
    canonical_path,
    {{ get_page_type("canonical_path") }} as page_type,
    if(
        canonical_path like "/organizations/%" or canonical_path like "/jobs/%/%/",
        {{ get_organization_slug("canonical_path") }},
        null
    ) as organization_slug,
    if(
        canonical_path like "/jobs/%/%/", {{ get_job_slug("canonical_path") }}, null
    ) as job_slug,
    query,
    country,
    search_type,
    device,
    search_appearance,
    sum(impressions) as n_impressions,
    sum(clicks) as n_clicks,
    sum(sum_position) as sum_position
from url_impressions
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
