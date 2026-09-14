{% macro get_organization_slug(path) %}
    split(regexp_replace({{ path }}, r'[/.]', '/'), '/')[safe_offset(2)]
{% endmacro %}
