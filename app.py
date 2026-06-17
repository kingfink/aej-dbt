import json
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import modal


@dataclass(frozen=True)
class ModelExport:
    name: str
    dataset: str
    relation: str


def load_model_exports(
    path: Path | None = None,
) -> tuple[ModelExport, ...]:
    path = path or Path(__file__).with_name("parquet_exports.json")
    with path.open() as file:
        config = json.load(file)
    return tuple(
        ModelExport(
            name=export["name"],
            dataset=export["dataset"],
            relation=export["relation"],
        )
        for export in config
    )


def build_export_query(export: ModelExport) -> str:
    return (
        f"select * from "
        f"`{os.environ['GCP_PROJECT_ID']}.{export.dataset}.{export.relation}`"
    )


def export_parquet_files(
    *,
    client,
    directory: Path,
) -> list[Path]:
    import pyarrow.parquet as parquet

    paths = []
    for export in load_model_exports():
        table = (
            client.query(build_export_query(export))
            .result()
            .to_arrow(create_bqstorage_client=False)
        )
        path = directory / f"{export.name}.parquet"
        parquet.write_table(table, path, compression="zstd")
        paths.append(path)
    return paths


def upload_parquet_files(*, client, bucket_name: str, paths: list[Path]) -> None:
    bucket = client.bucket(bucket_name)
    for path in paths:
        blob = bucket.blob(path.name)
        blob.cache_control = "no-cache"
        blob.upload_from_filename(
            str(path),
            content_type="application/vnd.apache.parquet",
        )


def create_google_credentials():
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_info(
        json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
    )


def create_bigquery_client():
    from google.cloud import bigquery

    return bigquery.Client(
        project=os.environ["GCP_PROJECT_ID"],
        credentials=create_google_credentials(),
    )


def create_gcs_client():
    from google.cloud import storage

    return storage.Client(
        project=os.environ["GCP_PROJECT_ID"],
        credentials=create_google_credentials(),
    )


def execute_parquet_publish() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        paths = export_parquet_files(
            client=create_bigquery_client(),
            directory=Path(temporary_directory),
        )
        upload_parquet_files(
            client=create_gcs_client(),
            bucket_name=os.environ["GCS_BUCKET_NAME"],
            paths=paths,
        )


def build_dbt_command(cmd: str, *, target: str = "dev") -> list[str]:
    args = shlex.split(cmd)
    command = [
        "dbt",
        *args,
        "--profiles-dir",
        ".",
    ]
    if not dbt_target(args):
        command.extend(["--target", target])
    return command


def dbt_target(args: list[str]) -> str:
    for index, arg in enumerate(args):
        if arg in {"--target", "-t"} and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith("--target="):
            return arg.partition("=")[2]
    return ""


def dbt_env(target: str, *, dbt_user: str = "", pr_number: str = "") -> dict[str, str]:
    if target == "dev":
        user = dbt_user or os.environ.get("AEJ_DBT_USER", "")
        if not user:
            raise ValueError("dbt_user is required for the dev target")
        return {"DBT_USER": user}
    if target == "ci":
        number = pr_number or os.environ.get("AEJ_DBT_PR_NUMBER", "")
        if not number:
            raise ValueError("pr_number is required for the ci target")
        return {"PR_NUMBER": number}
    return {}


def execute_dbt(
    cmd: str = "build",
    target: str = "",
    dbt_user: str = "",
    pr_number: str = "",
) -> None:
    target = (
        dbt_target(shlex.split(cmd))
        or target
        or os.environ.get("AEJ_DBT_TARGET", "dev")
    )
    subprocess.run(
        build_dbt_command(cmd, target=target),
        check=True,
        env=os.environ | dbt_env(target, dbt_user=dbt_user, pr_number=pr_number),
    )


def ping_healthcheck(ping_url: str, signal: str = "") -> None:
    url = ping_url.rstrip("/")
    if signal:
        url = f"{url}/{signal}"
    try:
        subprocess.run(
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--max-time",
                "5",
                "--retry",
                "3",
                url,
            ],
            check=False,
        )
    except OSError as error:
        print(f"Healthchecks.io ping failed: {error}")


app = modal.App("aej-dbt")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ca-certificates", "curl", "git", "jq")
    .pip_install(
        "google-cloud-bigquery>=3.38,<4",
        "google-cloud-storage>=3,<4",
        "pyarrow>=20,<21",
    )
    .add_local_file("scripts/install-dbt-fusion", "/tmp/install-dbt-fusion", copy=True)
    .run_commands("bash /tmp/install-dbt-fusion /usr/local/bin")
    .workdir("/workspace/aej-dbt")
    # Install dbt packages at build time so they are cached as an image layer.
    # Only the dependency-defining files go in first, so this layer (and the
    # `dbt deps` run below) is reused until one of them changes. Dummy env vars
    # let profiles.yml render; `dbt deps` never connects to BigQuery.
    .add_local_file("packages.yml", "/workspace/aej-dbt/packages.yml", copy=True)
    # The lockfile pins the exact resolved version/commit of every package, so
    # copying it in makes the cache key for the `dbt deps` layer below track the
    # locked revision. Moving an unpinned git dep (e.g. a fork's HEAD) then busts
    # this layer as soon as `dbt deps` is re-run locally and the lock changes.
    .add_local_file(
        "package-lock.yml", "/workspace/aej-dbt/package-lock.yml", copy=True
    )
    .add_local_file(
        "scripts/dbt-deps", "/workspace/aej-dbt/scripts/dbt-deps", copy=True
    )
    .add_local_file("dbt_project.yml", "/workspace/aej-dbt/dbt_project.yml", copy=True)
    .add_local_file("profiles.yml", "/workspace/aej-dbt/profiles.yml", copy=True)
    .run_commands("bash scripts/dbt-deps")
    .add_local_dir(
        ".",
        remote_path="/workspace/aej-dbt",
        ignore=[
            ".env*",
            ".git",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "dbt_packages",
            "logs",
            "target",
        ],
    )
)

bigquery_secret = modal.Secret.from_name(
    "aej-dbt-bq",
    required_keys=["GCP_PROJECT_ID", "SERVICE_ACCOUNT_JSON", "GCS_BUCKET_NAME"],
)

healthchecks_secret = modal.Secret.from_name(
    "aej-dbt-healthchecks",
    required_keys=["HEALTHCHECKS_PING_URL"],
)

# Persists the date of the last weekly full refresh so the schedule can run one
# without depending on the cron's exact shape. Created on first use.
state = modal.Dict.from_name("aej-dbt-state", create_if_missing=True)


def should_full_refresh(now: datetime, last_full_refresh: str) -> bool:
    """Whether this run should be the weekly full refresh.

    True on the first production run of each Sunday (UTC). Driven by the
    persisted ``last_full_refresh`` marker rather than the clock, so it stays
    correct if the cron cadence ever changes: every Sunday run sees a stale
    marker only until the day's first run claims the date.
    """
    return now.weekday() == 6 and last_full_refresh != now.date().isoformat()


@app.function(image=image, secrets=[bigquery_secret], timeout=60 * 60)
def run_dbt(
    cmd: str = "build",
    target: str = "",
    dbt_user: str = "",
    pr_number: str = "",
) -> None:
    execute_dbt(
        cmd=cmd,
        target=target,
        dbt_user=dbt_user,
        pr_number=pr_number,
    )


@app.function(image=image, secrets=[bigquery_secret], timeout=60 * 60)
def publish_parquet() -> None:
    execute_parquet_publish()


@app.function(
    image=image,
    secrets=[bigquery_secret, healthchecks_secret],
    timeout=60 * 60,
    schedule=modal.Cron("0 */6 * * *"),
)
def scheduled_production_sync() -> None:
    ping_url = os.environ["HEALTHCHECKS_PING_URL"]
    now = datetime.now(UTC)
    previous = state.get("last_full_refresh", "")
    full_refresh = should_full_refresh(now, previous)
    if full_refresh:
        # Claim the day up front so a concurrent or later Sunday run sees the
        # date as taken and stays incremental, never starting a second refresh.
        state["last_full_refresh"] = now.date().isoformat()
    ping_healthcheck(ping_url, "start")
    try:
        execute_dbt(
            cmd="build --full-refresh" if full_refresh else "build",
            target="prd",
        )
        execute_parquet_publish()
    except Exception:
        if full_refresh:
            # Release the claim so the next Sunday run retries the refresh.
            state["last_full_refresh"] = previous
        ping_healthcheck(ping_url, "fail")
        raise
    ping_healthcheck(ping_url)


def dispatch(
    *,
    cmd: str = "build",
    target: str = "",
    dbt_user: str = "",
    pr_number: str = "",
    publish: bool = False,
) -> None:
    if publish:
        publish_parquet.remote()
        return

    run_dbt.remote(
        cmd=cmd,
        target=target,
        dbt_user=dbt_user,
        pr_number=pr_number,
    )


@app.local_entrypoint()
def main(
    cmd: str = "build",
    target: str = "",
    dbt_user: str = "",
    pr_number: str = "",
    publish: bool = False,
) -> None:
    dispatch(
        cmd=cmd,
        target=target,
        dbt_user=dbt_user,
        pr_number=pr_number,
        publish=publish,
    )
