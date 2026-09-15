{% macro annualize_salary(amount, unit) %}
    safe_cast(
        safe_multiply(
            {{ amount }},
            case
                {{ unit }}
                when 'HOUR'
                then 2080
                when 'DAY'
                then 260
                when 'WEEK'
                then 52
                when 'MONTH'
                then 12
                when 'YEAR'
                then 1
            end
        ) as int64
    )
{% endmacro %}
