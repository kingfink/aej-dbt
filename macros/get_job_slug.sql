{% macro get_job_slug(file_path) %}
    split(regexp_replace(file_path, r'[/.]', '/'), '/')[safe_offset(3)]
{% endmacro %}
