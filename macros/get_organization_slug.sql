{% macro get_organization_slug(path) %}
    nullif(split(regexp_replace({{ path }}, r'[/.]', '/'), '/')[safe_offset(2)], '')
{% endmacro %}
