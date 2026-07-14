{% macro normalize_event_type(event_type_expression) %}
    case
        lower(nullif({{ event_type_expression }}, ""))
        when "processed"
        then "sent"
        when "open"
        then "opened"
        when "click"
        then "clicked"
        when "group_resubscribe"
        then "resubscribed"
        else replace(lower(nullif({{ event_type_expression }}, "")), "email.", "")
    end
{% endmacro %}
