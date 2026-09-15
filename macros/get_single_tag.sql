{% macro get_single_tag(tags, values) %}
    (
        select if(count(*) = 1, any_value(t), null)
        from unnest({{ tags }}) as t
        where
            t in (
                {%- for value in values %}
                    "{{ value }}"{{ "," if not loop.last }}
                {%- endfor %}
            )
    )
{% endmacro %}
