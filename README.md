# aej-dbt

dbt models for Analytics Engineering Jobs, executed on Modal against BigQuery.

## Setup

```bash
uv sync --locked
modal setup
cp .envrc.example .envrc
# Set AEJ_DBT_USER in .envrc
direnv allow
```

Create the Modal secret `aej-dbt-bq` with `SERVICE_ACCOUNT_JSON` containing the service-account JSON.

Grant the service account BigQuery User (`roles/bigquery.user`) and BigQuery Data Editor (`roles/bigquery.dataEditor`) on the `analytics-engineering-jobs` project. See the [dbt BigQuery setup docs](https://docs.getdbt.com/docs/local/connect-data-platform/bigquery-setup#required-permissions).

## Run

```bash
mdbt                         # dbt build
mdbt run
mdbt test
mdbt build --select model_name
mdbt test --target prd
```

Targets write to:

- `dev`: `dbt_dev_<user>`
- `ci`: `dbt_ci_<PR number>`
- `prd`: `dbt_prd`

## Checks

```bash
uv run pre-commit run --all-files
uv run python -m unittest discover -s tests
```
