select distinct
    {{ dbt_utils.generate_surrogate_key(["page_path"]) }} as page_id,
    page_path,
    {{ get_page_type("page_path") }} as page_type
from {{ ref("stg_google_search_console__url_impressions") }}
