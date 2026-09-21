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

The deployed public files are available at:

```text
https://storage.googleapis.com/aej-data/jobs.parquet
https://storage.googleapis.com/aej-data/organizations.parquet
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

The exported relations have enforced dbt contracts. Because publishing selects every model column, the contracted column names and data types in `models/marts/marts.yml` define the public Parquet schemas. Treat changes to those schemas as public interface changes.

Both objects use `Cache-Control: no-cache`. Because they are updated separately, clients may briefly see files from different publishes.

### Job salary definitions

`parquet_exports.json` continues to publish every column of `dbt_prd.dim_jobs` to `jobs.parquet`. The additive interface preserves `salary` and `tags` and adds only `salary_annual_min`, `salary_annual_max`, `salary_annual_midpoint`, `is_remote`, `level`, and `role_type`. Existing columns and the export path keep their meanings.

The normalized observations come from reviewed USD base-pay fields in site frontmatter. dbt does not parse salary text or descriptions, infer missing periods, or convert currencies. Explicit periods win over the stored `YEAR` fallback. Upstream extraction validates finite, positive, ordered bounds, provenance, and periods; staging data tests check these guarantees rather than repeating them as model filters. A single amount is usable when its bounds are equal. Broad combined location bands remain usable and there is no upper salary ceiling.

`stg_jobs` annualizes the two bounds through the shared `annualize_salary` macro; `dim_jobs` exposes them alongside warehouse keys. Annualization uses 2,080 hours, 260 days, 52 weeks, or 12 months and stores each bound as an INT64 rounded to the nearest whole dollar. Jobs without usable pay have null annual bounds and remain in the dimension so coverage retains its denominator. `is_remote` is true only when the Remote tag is present; false does not establish onsite work, and `location` retains geographic restrictions. `level` and `role_type` hold a job's single level tag and single Individual Contributor or People Manager tag, and are null when a job has none or several, as a few legacy inactive jobs do.

`fct_jobs_daily` has one row per UTC date and listed job, from the added date through the removal date, or through the current date while the job is active. Job attributes stay in `dim_jobs` and reflect current state. Inactive jobs without a removal date, or with a removal date before the added date, have no rows because their listing period is unknown. Steep reads the latest date of this fact for current coverage and pay summaries, so every summary carries its as-of date.

Consumers should use these definitions:

- **Current coverage:** count jobs where `is_active = true`; the numerator additionally requires both annual salary bounds. Label the percentage as usable USD salary coverage, not disclosure in any currency.
- **Pay by level or remote status:** among active jobs with both annual bounds, use `salary_annual_midpoint`, which `dim_jobs` derives as `(salary_annual_min + salary_annual_max) / 2`, and compute its approximate median and 25th/75th percentiles with BigQuery `approx_quantiles`, used for simplicity because `percentile_cont` is not available as an aggregate. Use `level`, `role_type`, and `is_remote` for the breakdowns. Show the salary observation count alongside pay summaries, because small groups are unstable; there is no minimum-observation threshold.
- **Context:** show an as-of date tied to the successful data refresh and check source freshness before publication. These are advertised ranges, not offers or earnings. Inferred periods, broad geographic bands, and the employer/location/level mix affect the results; a change in posting medians does not establish a market-pay trend.

The upstream `aej-dlt` job-content load must include the normalized frontmatter before these columns can populate. Build and test the models after that load, then publish through the existing `mpub` flow. Steep metrics and newsletter/site presentation are the next consumers described in [the revised salary scope](https://github.com/kingfink/analytics-engineering-jobs/issues/1844#issuecomment-5681150555).

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

The first Sunday run in UTC performs a full refresh; all other runs are incremental. `base_ga4__events` and `base_ga4__users` remain incremental because `dbt_project.yml` sets `+full_refresh: false` for them. Snapshots ignore `--full-refresh`, so the weekly refresh keeps the site-content history in `snp_jobs` and `snp_organizations`. The Search Console microbatch facts rebuild every monthly batch from their `begin` date during the refresh, which refreshes job and organization keys on older months. `fct_web_events` rebuilds every event during the refresh, which fills any gap left by a sync outage longer than its three-day lookback, picks up older PostHog backfills, and refreshes dimension keys on older events. A `modal.Dict` named `aej-dbt-state` tracks the weekly refresh and releases a failed claim so the next run can retry. After a successful build, the sync saves its manifest to the `aej-dbt-prod-state` Modal volume for Slim CI.

The scheduled function sends `/start` when it begins, a success ping after both dbt and Parquet publishing finish, and `/fail` if either step raises an error. Healthchecks pings are best-effort: monitoring outages do not block the sync.

Deploy the app to activate or update the schedule:

```bash
uv run modal deploy app.py
```

`modal run app.py` remains useful for manual runs, but it creates an ephemeral app and does not activate schedules.

### Continuous deployment

Pull requests run `Ruff`, `Unit tests`, `dbt parse`, and `dbt build` checks. Pushes to `master` run Ruff, unit tests, and dbt parse before the `Deploy` workflow updates the Modal app, then publishes Parquet from the deployed app as a smoke test.

The `dbt parse` check installs dbt locally on the GitHub-hosted runner, resolves the locked packages, and parses the project without warehouse credentials. It runs for every pull request, including pull requests from forks, in parallel with `dbt build`.

The `dbt build` check runs in Modal for pull requests whose branch is in this repository. It uses the `ci` target and writes to the pull request's isolated `dbt_ci_<PR number>` dataset. A dbt `on-run-start` hook configures that dataset with a 30-day default table and view expiration before dbt creates relations. BigQuery removes expired relations, while the empty dataset is intentionally retained. Pull requests from forks skip this credentialed check because GitHub does not provide repository secrets to fork workflows.

The check is Slim CI: it builds modified project resources and their descendants and defers other parents to production, using the manifest from the last successful production sync. Without that manifest, it builds every project-owned resource.

CI does not `dbt clone` unmodified incremental descendants from production, so they rebuild full history in a new pull request's dataset. Cloning saved only about 30 seconds and would stop CI from checking older rows; revisit it if those rebuilds grow to several minutes.

Model commands should go through `mdbt`, which keeps Modal dispatch, target selection, and package-lock handling in one place. Local shells can use `mdbt` because `.envrc` adds `bin` to `PATH`; GitHub Actions uses the explicit path:

```bash
AEJ_DBT_TARGET=ci AEJ_DBT_PR_NUMBER=123 ./bin/mdbt build --select state:modified+,package:this --defer --state /prod-state
```

Configure the default-branch ruleset to require the exact check names `Ruff`, `Unit tests`, `dbt parse`, and `dbt build`. Keep the workflow-level dbt trigger unfiltered so required check names are always reported; `package:this` inside the build keeps the installed GA4 package's models from being rebuilt.

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
