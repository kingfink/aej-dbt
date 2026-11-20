{#
  Elementary needs its test-results hooks to run inside the `test`
  materialization. Project macros take priority over package macros with the
  same name, so re-declaring dbt-core's default materialization here is what
  lets Elementary's on-run-end collection see every test result, including
  tests that do not use `--store-failures`.
#}
{% materialization test, default %}

  {% set relations = [] %}

  {% if not(should_store_failures()) %}

      {% set compiled_code = get_rendered_statement(sql) %}

  {% else %}

      {%- set identifier = model['alias'] -%}
      {%- set old_relation = adapter.get_relation(database=database, schema=schema, identifier=identifier) -%}
      {%- set target_relation = api.Relation.create(
          identifier=identifier, schema=schema, database=database, type='table') -%}

      {% if old_relation %}
          {% do adapter.drop_relation(old_relation) %}
      {% endif %}

      {% call statement(auto_begin=True) %}
          {{ create_table_as(False, target_relation, sql) }}
      {% endcall %}

      {% do relations.append(target_relation) %}

      {% set compiled_code = "select * from " ~ target_relation %}

  {% endif %}

  {% call statement('main', fetch_result=True) %}
      {{ get_test_sql(compiled_code, fail_calc, warn_if, error_if, limit) }}
  {% endcall %}

  {{ adapter.commit() }}

  {{ return({'relations': relations}) }}

{% endmaterialization %}
