with
    url_impressions as (
        select
            data_date,
            concat(
                rtrim(regexp_extract(url, r"^https?://[^/]+([^?#]*)"), "/"), "/"
            ) as canonical_path,
            query,
            is_anonymized_query,
            country,
            lower(search_type) as search_type,
            lower(device) as device,
            is_job_listing,
            is_job_details,
            impressions,
            clicks,
            sum_position
        from {{ source("search_console", "searchdata_url_impression") }}
    )

select
    {{
        dbt_utils.generate_surrogate_key(
            [
                "data_date",
                "canonical_path",
                "query",
                "is_anonymized_query",
                "country",
                "search_type",
                "device",
                "is_job_listing",
                "is_job_details",
            ]
        )
    }} as url_impression_id,
    data_date,
    canonical_path,
    query,
    is_anonymized_query,
    country,
    search_type,
    device,
    is_job_listing,
    is_job_details,
    sum(impressions) as impressions,
    sum(clicks) as clicks,
    sum(sum_position) as sum_position
from url_impressions
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
