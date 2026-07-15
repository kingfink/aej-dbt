{% test is_normalized_email_address(model, column_name) %}
    select {{ column_name }}
    from {{ model }}
    where
        {{ column_name }} is not null
        and {{ column_name }} != {{ normalize_email_address(column_name) }}
{% endtest %}
