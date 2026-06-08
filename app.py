import hashlib
import json
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import modal

import publisher

PROJECT_ID = "analytics-engineering-jobs"
PRODUCTION_DATASET = "dbt_prd"


@dataclass(frozen=True)
class ModelExport:
    model: str
    relation: str
    order_by: tuple[str, ...]


MODEL_EXPORTS = (
    ModelExport(
        model="jobs",
        relation="stg_jobs",
        order_by=("organization_slug", "job_slug"),
    ),
    ModelExport(
        model="organizations",
        relation="stg_organizations",
        order_by=("organization_slug",),
    ),
)


class R2Store:
    def __init__(self, *, client, bucket: str):
        self.client = client
        self.bucket = bucket

    def upload_file(
        self,
        path: Path,
        key: str,
        *,
        metadata: publisher.ObjectMetadata,
    ) -> None:
        self.client.upload_file(
            str(path),
            self.bucket,
            key,
            ExtraArgs={
                "ContentType": metadata.content_type,
                "CacheControl": metadata.cache_control,
            },
        )

    def put_json(
        self,
        key: str,
        payload: dict[str, object],
        *,
        metadata: publisher.ObjectMetadata,
    ) -> None:
        body = (
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        )
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=metadata.content_type,
            CacheControl=metadata.cache_control,
        )


def build_export_query(export: ModelExport) -> str:
    relation = f"`{PROJECT_ID}.{PRODUCTION_DATASET}.{export.relation}`"
    order_by = ", ".join(f"`{column}`" for column in export.order_by)
    return f"select * from {relation} order by {order_by}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_parquet_artifacts(
    *,
    client,
    directory: Path,
    generated_at: datetime,
) -> list[publisher.Artifact]:
    import pyarrow.parquet as parquet

    release_id = publisher.release_id_for(generated_at)
    artifacts = []
    for export in MODEL_EXPORTS:
        table = (
            client.query(build_export_query(export))
            .result()
            .to_arrow(create_bqstorage_client=False)
        )
        path = directory / f"{export.model}.parquet"
        parquet.write_table(table, path, compression="zstd")
        artifacts.append(
            publisher.Artifact(
                model=export.model,
                key=f"releases/{release_id}/{path.name}",
                path=path,
                rows=table.num_rows,
                size=path.stat().st_size,
                sha256=sha256_file(path),
            )
        )
    return artifacts


def create_bigquery_client():
    from google.cloud import bigquery
    from google.oauth2 import service_account

    service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info
    )
    return bigquery.Client(project=PROJECT_ID, credentials=credentials)


def create_r2_store() -> R2Store:
    import boto3

    account_id = os.environ["R2_ACCOUNT_ID"]
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    return R2Store(client=client, bucket=os.environ["R2_BUCKET_NAME"])


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
    required_keys=["SERVICE_ACCOUNT_JSON"],
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


@app.function(image=image, secrets=[bigquery_secret], timeout=60 * 60)
def run_dbt(
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


@app.function(
    image=image,
    secrets=[bigquery_secret, r2_secret],
    timeout=60 * 60,
)
def publish_parquet() -> dict[str, object]:
    generated_at = datetime.now(UTC).replace(microsecond=0)
    release_id = publisher.release_id_for(generated_at)
    with tempfile.TemporaryDirectory() as temporary_directory:
        artifacts = export_parquet_artifacts(
            client=create_bigquery_client(),
            directory=Path(temporary_directory),
            generated_at=generated_at,
        )
        return publisher.publish_release(
            store=create_r2_store(),
            release_id=release_id,
            generated_at=generated_at,
            artifacts=artifacts,
        )


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
