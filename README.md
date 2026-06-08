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

Create the Modal secret `aej-dbt-bq` with:

```text
GCP_PROJECT_ID
SERVICE_ACCOUNT_JSON
```

`SERVICE_ACCOUNT_JSON` should contain the service-account JSON.

Grant the service account BigQuery User (`roles/bigquery.user`) and BigQuery Data
Editor (`roles/bigquery.dataEditor`) on the project configured by
`GCP_PROJECT_ID`. See the
[dbt BigQuery setup docs](https://docs.getdbt.com/docs/local/connect-data-platform/bigquery-setup#required-permissions).

Create the Modal secret `aej-dbt-healthchecks` with the Healthchecks.io ping URL:

```bash
uv run modal secret create aej-dbt-healthchecks \
  HEALTHCHECKS_PING_URL=https://hc-ping.com/<check-uuid>
```

### R2 publishing

Create a Cloudflare R2 bucket and an R2 access key scoped to object read/write
access on that bucket. Create the Modal secret `aej-dbt-r2` with:

```text
R2_ACCOUNT_ID
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET_NAME
```

For production browser access, connect an
[R2 custom domain](https://developers.cloudflare.com/r2/data-access/public-buckets/#connect-a-bucket-to-a-custom-domain)
instead of using the rate-limited `r2.dev` URL.

Configure the bucket's
[CORS policy](https://developers.cloudflare.com/r2/buckets/cors/) for the
Netlify site and local development:

```json
[
  {
    "AllowedOrigins": [
      "https://your-netlify-domain.example",
      "http://localhost:3000"
    ],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["Range"],
    "ExposeHeaders": [
      "Accept-Ranges",
      "Content-Length",
      "Content-Range",
      "ETag"
    ],
    "MaxAgeSeconds": 3600
  }
]
```

If the bucket was already serving through a custom domain, purge that hostname's
cache after changing CORS so cached objects receive the new response headers.

## Run

```bash
mdbt                         # dbt build
mdbt run
mdbt test
mdbt build --select model_name
mdbt test --target prd
```

Build production models, then publish the Parquet files:

```bash
mdbt build --target prd
mpub
```

Publishing overwrites these fixed R2 objects:

```text
jobs.parquet
organizations.parquet
```

Configure the output names, datasets, and relations in `parquet_exports.json`.

Both objects are uploaded with `Cache-Control: no-cache`. Because they are
updated separately, clients may briefly see files from different publishes.

Targets write to:

- `dev`: `dbt_dev_<user>`
- `ci`: `dbt_ci_<PR number>`
- `prd`: `dbt_prd`

## Scheduled production sync

The deployed Modal app runs `dbt build --target prd` and then publishes the
Parquet files four times daily, at 00:00, 06:00, 12:00, and 18:00 UTC:

```python
modal.Cron("0 */6 * * *")
```

Configure a Healthchecks.io check named `aej-dbt production sync` with:

- Schedule type: Cron
- Cron expression: `0 */6 * * *`
- Time zone: UTC
- Grace time: 60 minutes
- Notification integration: email, Slack, or your preferred Healthchecks.io alert destination

The scheduled function sends `/start` when it begins, a success ping after both
dbt and Parquet publishing finish, and `/fail` if either step raises an error.
Healthchecks pings are best-effort: monitoring outages do not block the sync.

Deploy the app to activate or update the schedule:

```bash
uv run modal deploy app.py
```

`modal run app.py` remains useful for manual runs, but it creates an ephemeral app and does not activate schedules.

## Checks

```bash
uv run pre-commit run --all-files
uv run python -m unittest discover -s tests
```
