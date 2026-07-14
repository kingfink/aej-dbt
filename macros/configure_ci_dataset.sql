{% macro configure_ci_dataset() %}
    {% if target.name == "ci" %}
        {% set expiration_days = 30 %}

        create schema if not exists `{{ target.project }}.{{ target.dataset }}`
        options(
            location = "US",
            default_table_expiration_days = {{ expiration_days }}
        );

        alter schema `{{ target.project }}.{{ target.dataset }}`
        set options(
            default_table_expiration_days = {{ expiration_days }}
        );
    {% endif %}
{% endmacro %}
