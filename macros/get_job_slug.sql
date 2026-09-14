{% macro get_job_slug(path) %}
    {#- Works for repository file paths (docs/jobs/{organization}/{job}.md) and
    site page paths (/jobs/{organization}/{job}/). Returns null for anything
    else, including legacy flat /jobs/{slug}/ paths. -#}
    {%- set segments = "split(regexp_replace(" ~ path ~ ", r'[/.]', '/'), '/')" -%}
    if(
        {{ segments }} [safe_offset(1)] = 'jobs',
        nullif({{ segments }} [safe_offset(3)], ''),
        null
    )
{% endmacro %}
