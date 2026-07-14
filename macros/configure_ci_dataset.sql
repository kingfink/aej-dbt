{% macro configure_ci_dataset() %}
    {% if target.name == "ci" %}
        {% set pr_number = env_var("PR_NUMBER") %}
        {% if target.type != "bigquery" %}
            {{ exceptions.raise_compiler_error("The ci target must use BigQuery") }}
        {% elif not pr_number.isdigit() %}
            {{ exceptions.raise_compiler_error("PR_NUMBER must contain only digits") }}
        {% endif %}
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
