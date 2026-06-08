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
GCS_BUCKET_NAME
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

### Parquet publishing

Create a public Cloud Storage bucket with uniform bucket-level access. Bucket
names are globally unique:

```bash
gcloud storage buckets create gs://<bucket-name> \
  --project=analytics-engineering-jobs \
  --location=US \
  --uniform-bucket-level-access \
  --no-public-access-prevention
```

Grant the dbt service account permission to replace objects, and allow public
reads:

```bash
gcloud storage buckets add-iam-policy-binding gs://<bucket-name> \
  --member=serviceAccount:<service-account-email> \
  --role=roles/storage.objectAdmin

gcloud storage buckets add-iam-policy-binding gs://<bucket-name> \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

Save this browser CORS policy outside the repository:

```json
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD"],
    "responseHeader": [
      "Accept-Ranges",
      "Content-Length",
      "Content-Range",
      "Content-Type",
      "ETag",
      "Range"
    ],
    "maxAgeSeconds": 3600
  }
]
```

Apply it with:

```bash
gcloud storage buckets update gs://<bucket-name> \
  --cors-file=<path-to-cors-json>
```

The files are then available at:

```text
https://storage.googleapis.com/<bucket-name>/jobs.parquet
https://storage.googleapis.com/<bucket-name>/organizations.parquet
```

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

Publishing overwrites these fixed Cloud Storage objects:

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

### Continuous deployment

GitHub Actions keeps lint, tests, and deployment in separate workflow files.
Pull requests run the `Lint` and `Tests` workflows directly. After a push to
`master`, the `Deploy` workflow calls those same reusable workflows and deploys
the Modal app only after both pass.

Create a Modal token for GitHub Actions, then add its values as repository
secrets under **Settings → Secrets and variables → Actions**:

```text
MODAL_TOKEN_ID
MODAL_TOKEN_SECRET
```

The workflow uses these credentials only for the `Deploy Modal` job. The
application's BigQuery, Cloud Storage, and Healthchecks values remain in Modal
Secrets and are not copied into GitHub.

## Checks

```bash
uv run pre-commit run --all-files
uv run python -m unittest discover -s tests
```
