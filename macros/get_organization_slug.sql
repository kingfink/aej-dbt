{% macro get_organization_slug(file_path) %}
    split(regexp_replace(file_path, r'[/.]', '/'), '/')[safe_offset(2)]
{% endmacro %}
