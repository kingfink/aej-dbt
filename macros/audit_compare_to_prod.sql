{% macro audit_compare_to_prod(model_unique_ids, prod_dataset="dbt_prd") %}
    {#
        Compares each named model's current-target relation against its
        counterpart in `prod_dataset` using dbt-labs/audit_helper, reporting
        row-count and schema differences to the run log without failing the
        run. A starting point for data-diff coverage now that Datafold's OSS
        tool is archived.

        Takes unique IDs rather than model names because a versioned model's
        name is ambiguous: `dim_email_campaigns` is both v1 and v2. The graph
        node carries the relation the model actually builds, including the
        version suffix in its alias, so no `ref()` call is needed.
    #}
    {% if execute %}
        {% for unique_id in model_unique_ids %}
            {% if unique_id not in graph.nodes %}
                {{
                    log(
                        "audit: skipped " ~ unique_id ~ ", not a node in the graph",
                        info=true,
                    )
                }}
            {% else %}
                {% set node = graph.nodes[unique_id] %}
                {% do audit_log_model_diff(node, prod_dataset) %}
            {% endif %}
        {% endfor %}
    {% endif %}
{% endmacro %}

{% macro audit_log_model_diff(node, prod_dataset) %}
    {#
        Resolves both relations before querying them. A deferred or unbuilt
        model has no relation in the current target, and a model added by the
        pull request has no counterpart in production yet; either way the
        comparison is skipped rather than failing on a missing table.
    #}
    {% set current_relation = adapter.get_relation(
        database=node["database"],
        schema=node["schema"],
        identifier=node["alias"],
    ) %}
    {% set prod_relation = adapter.get_relation(
        database=node["database"],
        schema=prod_dataset,
        identifier=node["alias"],
    ) %}
    {% if current_relation is none %}
        {{
            log(
                "audit: skipped "
                ~ node["alias"]
                ~ ", not built in "
                ~ node["schema"],
                info=true,
            )
        }}
    {% elif prod_relation is none %}
        {{
            log(
                "audit: skipped "
                ~ node["alias"]
                ~ ", no counterpart in "
                ~ prod_dataset,
                info=true,
            )
        }}
    {% else %} {% do audit_log_relation_diff(current_relation, prod_relation) %}
    {% endif %}
{% endmacro %}

{% macro audit_log_relation_diff(current_relation, prod_relation) %}
    {#
        `audit_helper.compare_row_counts` returns one row per relation from a
        bare `union all`, so the rows are keyed on the rendered relation name
        rather than read positionally: BigQuery does not guarantee which half
        of a `union all` comes back first, and reading them by position can
        invert the logged difference.
    #}
    {% set row_counts = run_query(
        audit_helper.compare_row_counts(current_relation, prod_relation)
    ) %}
    {% set n_rows_by_relation = {} %}
    {% for row in row_counts.rows %}
        {% do n_rows_by_relation.update({row["relation_name"]: row["total_records"]}) %}
    {% endfor %}
    {% set n_current_rows = n_rows_by_relation.get(current_relation | string) %}
    {% set n_prod_rows = n_rows_by_relation.get(prod_relation | string) %}

    {% if n_current_rows is none or n_prod_rows is none %}
        {{
            log(
                "audit: "
                ~ current_relation.identifier
                ~ " row counts could not be matched to their relations",
                info=true,
            )
        }}
    {% else %}
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
    {% endif %}

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
