{% macro get_frontmatter_value(json_frontmatter, json_key, output_type="string") %}
    cast(json_value({{ json_frontmatter }}, '{{ json_key }}') as {{ output_type }})
{% endmacro %}
