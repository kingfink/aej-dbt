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

Create the Modal secret `aej-dbt-healthchecks` with the Healthchecks.io ping URL:

```bash
uv run modal secret create aej-dbt-healthchecks \
  HEALTHCHECKS_PING_URL=https://hc-ping.com/<check-uuid>
```

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

## Scheduled production build

The deployed Modal app runs `dbt build --target prd` hourly with:

```python
modal.Cron("0 * * * *")
```

Configure a Healthchecks.io check named `aej-dbt hourly build` with:

- Schedule type: Cron
- Cron expression: `0 * * * *`
- Time zone: UTC
- Grace time: 60 minutes
- Notification integration: email, Slack, or your preferred Healthchecks.io alert destination

The scheduled function sends `/start` when it begins, a success ping after dbt exits successfully, and `/fail` if dbt raises an error. Healthchecks pings are best-effort: monitoring outages do not block the dbt build.

Deploy the app to activate or update the hourly schedule:

```bash
uv run modal deploy app.py
```

`modal run app.py` remains useful for manual runs, but it creates an ephemeral app and does not activate schedules.

## Checks

```bash
uv run pre-commit run --all-files
uv run python -m unittest discover -s tests
```
