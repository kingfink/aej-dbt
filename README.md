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

Build production models, then publish a new Parquet release:

```bash
mdbt build --target prd
mpublish
```

Publishing writes versioned, immutable objects and updates `latest.json` only
after the release is complete:

```text
releases/<release-id>/jobs.parquet
releases/<release-id>/organizations.parquet
releases/<release-id>/manifest.json
latest.json
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
