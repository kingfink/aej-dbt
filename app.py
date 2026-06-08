import json
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import modal


@dataclass(frozen=True)
class ModelExport:
    name: str
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
            relation=export["relation"],
        )
        for export in config
    )


def build_export_query(export: ModelExport) -> str:
    return f"select * from `{os.environ['GCP_PROJECT_ID']}.dbt_prd.{export.relation}`"


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


def upload_parquet_files(*, client, bucket: str, paths: list[Path]) -> None:
    for path in paths:
        client.upload_file(
            str(path),
            bucket,
            path.name,
            ExtraArgs={
                "ContentType": "application/vnd.apache.parquet",
                "CacheControl": "no-cache",
            },
        )


def create_bigquery_client():
    from google.cloud import bigquery
    from google.oauth2 import service_account

    service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info
    )
    return bigquery.Client(
        project=os.environ["GCP_PROJECT_ID"],
        credentials=credentials,
    )


def create_r2_client():
    import boto3

    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
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
        "boto3>=1.40,<2",
        "google-cloud-bigquery>=3.38,<4",
        "pyarrow>=20,<21",
    )
    .run_commands(
        "export SHELL=/bin/bash && "
        "curl -fsSL https://public.cdn.getdbt.com/fs/install/install.sh"
        " | sh -s -- --version stable --to /usr/local/bin"
    )
    .workdir("/workspace/aej-dbt")
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
    required_keys=["GCP_PROJECT_ID", "SERVICE_ACCOUNT_JSON"],
)
r2_secret = modal.Secret.from_name(
    "aej-dbt-r2",
    required_keys=[
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
    ],
)

healthchecks_secret = modal.Secret.from_name(
    "aej-dbt-healthchecks",
    required_keys=["HEALTHCHECKS_PING_URL"],
)


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


@app.function(image=image, secrets=[bigquery_secret, r2_secret], timeout=60 * 60)
def publish_parquet() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        paths = export_parquet_files(
            client=create_bigquery_client(),
            directory=Path(temporary_directory),
        )
        upload_parquet_files(
            client=create_r2_client(),
            bucket=os.environ["R2_BUCKET_NAME"],
            paths=paths,
        )


@app.function(
    image=image,
    secrets=[bigquery_secret, healthchecks_secret],
    timeout=60 * 60,
    schedule=modal.Cron("0 * * * *"),
)
def hourly_dbt_build() -> None:
    ping_url = os.environ["HEALTHCHECKS_PING_URL"]
    ping_healthcheck(ping_url, "start")
    try:
        execute_dbt(target="prd")
    except Exception:
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
