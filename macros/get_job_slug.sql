{% macro get_job_slug(path) %}
    nullif(split(regexp_replace({{ path }}, r'[/.]', '/'), '/')[safe_offset(3)], '')
{% endmacro %}
