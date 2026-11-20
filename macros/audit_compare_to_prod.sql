{% macro audit_compare_to_prod(model_names, prod_dataset="dbt_prd") %}
    {#
        Compares each named model's current-target relation against its
        counterpart in `prod_dataset` using dbt-labs/audit_helper, reporting
        row-count and schema differences to the run log without failing the
        run. A starting point for data-diff coverage now that Datafold's OSS
        tool is archived.
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
    {% set row_counts = run_query(
        audit_helper.compare_row_counts(current_relation, prod_relation)
    ) %}
    {% set n_current_rows = row_counts.rows[0]["total_records"] %}
    {% set n_prod_rows = row_counts.rows[1]["total_records"] %}

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

    {% set column_diffs = run_query(
        audit_helper.compare_relation_columns(current_relation, prod_relation)
    ) %}
    {% set mismatched_columns = [] %}
    {% for row in column_diffs.rows %}
        {% if not row["in_both"] or not row["has_data_type_match"] %}
            {% do mismatched_columns.append(row["column_name"]) %}
        {% endif %}
    {% endfor %}
    {% if mismatched_columns %}
        {{
            log(
                "audit: "
                ~ current_relation.identifier
                ~ " schema diff, mismatched columns="
                ~ mismatched_columns,
                info=true,
            )
        }}
    {% endif %}
{% endmacro %}
