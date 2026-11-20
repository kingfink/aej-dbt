{% macro audit_compare_to_prod(model_names, prod_dataset="dbt_prd") %}
    {#
        Compares each named model's current-target relation against its
        counterpart in `prod_dataset`, reporting row-count and schema
        differences to the run log without failing the run. A starting point
        for data-diff coverage now that Datafold's OSS tool is archived; see
        the dbt-labs/audit_helper package for richer value-level diffing once
        its package-lock entry can be generated with registry access.
    #}
    {% if execute %}
        {% for model_name in model_names %}
            {% set current_relation = ref(model_name) %}
            {% set prod_relation = api.Relation.create(
                database=current_relation.database,
                schema=prod_dataset,
                identifier=current_relation.identifier,
            ) %}
            {% do audit_log_relation_diff(current_relation, prod_relation) %}
        {% endfor %}
    {% endif %}
{% endmacro %}

{% macro audit_log_relation_diff(current_relation, prod_relation) %}
    {% set row_count_query %}
        select
            (select count(*) from {{ current_relation }}) as n_current_rows,
            (select count(*) from {{ prod_relation }}) as n_prod_rows
    {% endset %}
    {% set row_counts = run_query(row_count_query) %}
    {% set n_current_rows = row_counts.columns[0].values()[0] %}
    {% set n_prod_rows = row_counts.columns[1].values()[0] %}

    {% set current_column_set = (
        adapter.get_columns_in_relation(current_relation)
        | map(attribute="name")
        | list
    ) %}
    {% set prod_column_set = (
        adapter.get_columns_in_relation(prod_relation)
        | map(attribute="name")
        | list
    ) %}
    {% set current_only = current_column_set | reject("in", prod_column_set) | list %}
    {% set prod_only = prod_column_set | reject("in", current_column_set) | list %}

    {{
        log(
            "audit: "
            ~ current_relation.identifier
            ~ " rows current="
            ~ n_current_rows
            ~ " prod="
            ~ n_prod_rows
            ~ " diff="
            ~ (n_current_rows - n_prod_rows),
            info=true,
        )
    }}
    {% if current_only or prod_only %}
        {{
            log(
                "audit: "
                ~ current_relation.identifier
                ~ " schema diff, current_only="
                ~ current_only
                ~ " prod_only="
                ~ prod_only,
                info=true,
            )
        }}
    {% endif %}
{% endmacro %}
