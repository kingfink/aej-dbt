select
    {{ dbt_utils.generate_surrogate_key(["alpha_3_code"]) }} as country_id,
    alpha_3_code,
    alpha_2_code,
    country_name,
    continent_name
from {{ ref("countries") }}
