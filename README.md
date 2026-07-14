# aej-dbt

dbt models for Analytics Engineering Jobs, executed on Modal against BigQuery.

## Setup

### Local

```bash
uv sync --locked
modal setup
cp .envrc.example .envrc
# Set AEJ_DBT_USER in .envrc
direnv allow
```

### GitHub Codespaces

Before creating a codespace, add these personal Codespaces secrets and scope them to this repository:

```text
GCP_PROJECT_ID
SERVICE_ACCOUNT_JSON
DBT_USER
```

Optionally add one provider key for dbt Wizard:

```text
ANTHROPIC_API_KEY
OPENAI_API_KEY
```

To reuse a local dbt Platform login, run `wizard login` locally and store the resulting credentials as a user-level Codespaces secret:

```bash
gh secret set DBT_WIZARD_AUTH_JSON \
  --user \
  --repos aej-dbt \
  < ~/.dbt/wizard/auth.json
```

Codespaces installs the Python and dbt toolchain automatically. On startup, it restores `~/.dbt/wizard/auth.json` only when the file is missing, preserving credentials that Wizard refreshes locally.

```bash
wizard
```

Wizard may still ask you to accept its Terms of Use. If credentials are missing, verify the secret scopes and restart the codespace. Replace `DBT_WIZARD_AUTH_JSON` only when a new codespace cannot refresh it.

### Modal secrets

Create the Modal secret `aej-dbt-bq` with:

```text
GCP_PROJECT_ID
SERVICE_ACCOUNT_JSON
GCS_BUCKET_NAME
```

Set `SERVICE_ACCOUNT_JSON` to the complete service-account JSON. Grant that account BigQuery User (`roles/bigquery.user`) and BigQuery Data Editor (`roles/bigquery.dataEditor`) on `GCP_PROJECT_ID`. See the [dbt BigQuery setup docs](https://docs.getdbt.com/docs/local/connect-data-platform/bigquery-setup#required-permissions).

Create the Modal secret `aej-dbt-healthchecks` with the Healthchecks.io ping URL:

```bash
uv run modal secret create aej-dbt-healthchecks \
  HEALTHCHECKS_PING_URL=https://hc-ping.com/<check-uuid>
```

### Parquet publishing

Create a public Cloud Storage bucket with uniform bucket-level access. Bucket names are globally unique:

```bash
gcloud storage buckets create gs://<bucket-name> \
  --project=analytics-engineering-jobs \
  --location=US \
  --uniform-bucket-level-access \
  --no-public-access-prevention
```

Grant the dbt service account permission to replace objects, and allow public reads:

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

Targets write to:

- `dev`: `dbt_dev_<user>`
- `ci`: `dbt_ci_<PR number>`
- `prd`: `dbt_prd`

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

Both objects use `Cache-Control: no-cache`. Because they are updated separately, clients may briefly see files from different publishes.

## Scheduled production sync

The deployed Modal app builds production and publishes Parquet files every six hours:

```python
modal.Cron("0 */6 * * *")
```

Configure a Healthchecks.io check named `aej-dbt production sync` with:

- Schedule type: Cron
- Cron expression: `0 */6 * * *`
- Time zone: UTC
- Grace time: 60 minutes
- Notification integration: email, Slack, or your preferred Healthchecks.io alert destination

The first Sunday run in UTC performs a full refresh; all other runs are incremental. `base_ga4__events` and `base_ga4__users` remain incremental because `dbt_project.yml` sets `+full_refresh: false` for them. A `modal.Dict` named `aej-dbt-state` tracks the weekly refresh and releases a failed claim so the next run can retry.

The scheduled function sends `/start` when it begins, a success ping after both dbt and Parquet publishing finish, and `/fail` if either step raises an error. Healthchecks pings are best-effort: monitoring outages do not block the sync.

Deploy the app to activate or update the schedule:

```bash
uv run modal deploy app.py
```

`modal run app.py` remains useful for manual runs, but it creates an ephemeral app and does not activate schedules.

### Continuous deployment

Pull requests run `Ruff`, `Unit tests`, `dbt parse`, and `dbt build` checks. Pushes to `master` run Ruff, unit tests, and dbt parse before the `Deploy` workflow updates the Modal app.

The `dbt parse` check installs dbt locally on the GitHub-hosted runner, resolves the locked packages, and parses the project without warehouse credentials. It runs for every pull request, including pull requests from forks.

The `dbt build` check runs project-owned models and their tests in Modal for pull requests whose branch is in this repository. It uses the `ci` target and writes to the pull request's isolated `dbt_ci_<PR number>` dataset. Pull requests from forks skip this credentialed check because GitHub does not provide repository secrets to fork workflows.

Model commands should go through `mdbt`, which keeps Modal dispatch, target selection, and package-lock handling in one place. Local shells can use `mdbt` because `.envrc` adds `bin` to `PATH`; GitHub Actions uses the explicit path:

```bash
AEJ_DBT_TARGET=ci AEJ_DBT_PR_NUMBER=123 ./bin/mdbt build --select package:this,resource_type:model
```

When an in-repository pull request closes, the cleanup workflow deletes its CI dataset and all contained relations. Cleanup is an application maintenance operation rather than a dbt command, so it calls the Modal entrypoint directly.

Configure the default-branch ruleset to require the exact check names `Ruff`, `Unit tests`, `dbt parse`, and `dbt build`. Keep the workflow-level dbt trigger unfiltered so required check names are always reported; selection inside the build limits warehouse work to project-owned models.

Create a Modal token for GitHub Actions, then add its values as repository secrets under **Settings → Secrets and variables → Actions**:

```text
MODAL_TOKEN_ID
MODAL_TOKEN_SECRET
```

The deploy and in-repository dbt CI jobs use these credentials. BigQuery, Cloud Storage, and Healthchecks values remain in Modal Secrets and are not copied into GitHub Actions.

## Checks

```bash
uv run pre-commit run --all-files
uv run python -m unittest discover -s tests
```
