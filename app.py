import os
import shlex
import subprocess

import modal


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


@app.local_entrypoint()
def main(
    cmd: str = "build",
    target: str = "",
    dbt_user: str = "",
    pr_number: str = "",
) -> None:
    run_dbt.remote(
        cmd=cmd,
        target=target,
        dbt_user=dbt_user,
        pr_number=pr_number,
    )
