-- search_appearance collapses these flags into one categorical, which silently
-- keeps only the first match if Google ever sets both on the same row.
select data_date, url, query, country, device, search_type
from {{ source("google_search_console", "searchdata_url_impression") }}
where is_job_listing and is_job_details
