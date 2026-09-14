{% macro get_organization_slug(path) %}
    {#- Works for repository file paths (docs/organizations/{organization}.md,
    docs/jobs/{organization}/{job}.md) and the matching site page paths.
    Returns null for anything else, including legacy flat /jobs/{slug}/ paths,
    whose single segment is not an organization. -#}
    {%- set segments = "split(regexp_replace(" ~ path ~ ", r'[/.]', '/'), '/')" -%}
    case
        {{ segments }} [safe_offset(1)]
        when 'organizations'
        then nullif({{ segments }} [safe_offset(2)], '')
        when 'jobs'
        then
            if(
                nullif({{ segments }} [safe_offset(3)], '') is not null,
                nullif({{ segments }} [safe_offset(2)], ''),
                null
            )
    end
{% endmacro %}
