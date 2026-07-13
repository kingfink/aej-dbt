{% macro normalize_email_address(email_expression) %}
    lower(trim({{ email_expression }}))
{% endmacro %}
