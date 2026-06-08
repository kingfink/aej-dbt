import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

import app


class FakeS3Client:
    def __init__(self):
        self.uploads = []

    def upload_file(self, filename, bucket, key, *, ExtraArgs):
        self.uploads.append((filename, bucket, key, ExtraArgs))


class DbtCommandTest(unittest.TestCase):
    def test_preserves_quoted_args_and_appends_shared_options(self):
        command = app.build_dbt_command(
            'run-operation grant_select --args \'{"role": "reporter"}\'',
            target="prd",
        )

        self.assertEqual(
            command,
            [
                "dbt",
                "run-operation",
                "grant_select",
                "--args",
                '{"role": "reporter"}',
                "--profiles-dir",
                ".",
                "--target",
                "prd",
            ],
        )

    def test_preserves_command_target_without_appending_another_target(self):
        command = app.build_dbt_command(
            "test --target prd --select tag:nightly",
            target="dev",
        )

        self.assertEqual(
            command,
            [
                "dbt",
                "test",
                "--target",
                "prd",
                "--select",
                "tag:nightly",
                "--profiles-dir",
                ".",
            ],
        )


class DbtRunTest(unittest.TestCase):
    def test_local_modal_function_uses_environment_defaults(self):
        env = {
            "GCP_PROJECT_ID": "configured-project",
            "SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
            "AEJ_DBT_USER": "tf",
        }

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.subprocess.run") as run,
        ):
            app.run_dbt.local()

        run.assert_called_once_with(
            ["dbt", "build", "--profiles-dir", ".", "--target", "dev"],
            check=True,
            env=env | {"DBT_USER": "tf"},
        )

    def test_explicit_arguments_override_environment_defaults(self):
        env = {
            "GCP_PROJECT_ID": "configured-project",
            "SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
            "AEJ_DBT_TARGET": "dev",
            "AEJ_DBT_USER": "tf",
        }

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.subprocess.run") as run,
        ):
            app.run_dbt.local(cmd="debug", target="ci", pr_number="123")

        run.assert_called_once_with(
            ["dbt", "debug", "--profiles-dir", ".", "--target", "ci"],
            check=True,
            env=env | {"PR_NUMBER": "123"},
        )

    def test_dbt_target_flag_overrides_environment_default(self):
        env = {
            "GCP_PROJECT_ID": "configured-project",
            "SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
            "AEJ_DBT_TARGET": "dev",
            "AEJ_DBT_USER": "tf",
        }

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.subprocess.run") as run,
        ):
            app.run_dbt.local(cmd="test --target prd")

        run.assert_called_once_with(
            ["dbt", "test", "--target", "prd", "--profiles-dir", "."],
            check=True,
            env=env,
        )

    def test_rejects_missing_dynamic_dataset_suffix(self):
        for target, message in [
            ("dev", "dbt_user is required"),
            ("ci", "pr_number is required"),
        ]:
            with (
                self.subTest(target=target),
                self.assertRaisesRegex(ValueError, message),
            ):
                app.dbt_env(target)


class AppDispatchTest(unittest.TestCase):
    def test_publish_mode_dispatches_to_parquet_publish_job(self):
        with (
            patch("app.run_dbt.remote") as run_dbt,
            patch("app.publish_parquet.remote") as publish_parquet,
        ):
            app.dispatch(publish=True)

        publish_parquet.assert_called_once_with()
        run_dbt.assert_not_called()

    def test_default_mode_dispatches_to_dbt_runner(self):
        with (
            patch("app.run_dbt.remote") as run_dbt,
            patch("app.publish_parquet.remote") as publish_parquet,
        ):
            app.dispatch(
                cmd="build --select stg_jobs",
                target="prd",
                dbt_user="tf",
                pr_number="123",
            )

        run_dbt.assert_called_once_with(
            cmd="build --select stg_jobs",
            target="prd",
            dbt_user="tf",
            pr_number="123",
        )
        publish_parquet.assert_not_called()


class ParquetPublishingAdapterTest(unittest.TestCase):
    def test_load_model_exports_reads_json_config(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "parquet_exports.json"
            config_path.write_text(
                json.dumps(
                    [
                        {
                            "name": "jobs",
                            "dataset": "published_models",
                            "relation": "stg_jobs",
                        },
                        {
                            "name": "organizations",
                            "dataset": "published_models",
                            "relation": "stg_organizations",
                        },
                    ]
                )
            )

            self.assertEqual(
                app.load_model_exports(config_path),
                (
                    app.ModelExport(
                        name="jobs",
                        dataset="published_models",
                        relation="stg_jobs",
                    ),
                    app.ModelExport(
                        name="organizations",
                        dataset="published_models",
                        relation="stg_organizations",
                    ),
                ),
            )

    def test_build_export_query_selects_relation(self):
        export = app.ModelExport(
            name="jobs",
            dataset="published_models",
            relation="stg_jobs",
        )

        with patch.dict("os.environ", {"GCP_PROJECT_ID": "configured-project"}):
            self.assertEqual(
                app.build_export_query(export),
                "select * from `configured-project.published_models.stg_jobs`",
            )

    def test_upload_parquet_files_uses_fixed_keys_and_no_cache(self):
        client = FakeS3Client()

        app.upload_parquet_files(
            client=client,
            bucket="aej-data",
            paths=[
                Path("/tmp/jobs.parquet"),
                Path("/tmp/organizations.parquet"),
            ],
        )

        self.assertEqual(
            client.uploads,
            [
                (
                    "/tmp/jobs.parquet",
                    "aej-data",
                    "jobs.parquet",
                    {
                        "ContentType": "application/vnd.apache.parquet",
                        "CacheControl": "no-cache",
                    },
                ),
                (
                    "/tmp/organizations.parquet",
                    "aej-data",
                    "organizations.parquet",
                    {
                        "ContentType": "application/vnd.apache.parquet",
                        "CacheControl": "no-cache",
                    },
                ),
            ],
        )


class ScheduledProductionSyncTest(unittest.TestCase):
    def test_runs_dbt_then_publish_and_reports_success(self):
        env = {
            "GCP_PROJECT_ID": "configured-project",
            "SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
            "HEALTHCHECKS_PING_URL": "https://hc-ping.com/check-id",
        }
        events = []

        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "app.ping_healthcheck",
                side_effect=lambda url, signal="": events.append(("ping", signal)),
            ),
            patch(
                "app.execute_dbt",
                side_effect=lambda **kwargs: events.append(("dbt", kwargs)),
            ),
            patch(
                "app.execute_parquet_publish",
                side_effect=lambda: events.append(("publish",)),
            ),
        ):
            app.scheduled_production_sync.local()

        self.assertEqual(
            events,
            [
                ("ping", "start"),
                ("dbt", {"target": "prd"}),
                ("publish",),
                ("ping", ""),
            ],
        )

    def test_dbt_failure_reports_failure_without_publishing(self):
        env = {
            "GCP_PROJECT_ID": "configured-project",
            "SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
            "HEALTHCHECKS_PING_URL": "https://hc-ping.com/check-id",
        }
        dbt_error = subprocess.CalledProcessError(1, ["dbt", "build"])

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.ping_healthcheck") as ping_healthcheck,
            patch("app.execute_dbt", side_effect=dbt_error),
            patch("app.execute_parquet_publish") as publish,
            self.assertRaises(subprocess.CalledProcessError),
        ):
            app.scheduled_production_sync.local()

        publish.assert_not_called()
        self.assertEqual(
            ping_healthcheck.call_args_list,
            [
                call("https://hc-ping.com/check-id", "start"),
                call("https://hc-ping.com/check-id", "fail"),
            ],
        )

    def test_publish_failure_reports_failure(self):
        env = {
            "GCP_PROJECT_ID": "configured-project",
            "SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
            "HEALTHCHECKS_PING_URL": "https://hc-ping.com/check-id",
        }
        publish_error = RuntimeError("R2 upload failed")

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.ping_healthcheck") as ping_healthcheck,
            patch("app.execute_dbt") as execute_dbt,
            patch("app.execute_parquet_publish", side_effect=publish_error),
            self.assertRaisesRegex(RuntimeError, "R2 upload failed"),
        ):
            app.scheduled_production_sync.local()

        execute_dbt.assert_called_once_with(target="prd")
        self.assertEqual(
            ping_healthcheck.call_args_list,
            [
                call("https://hc-ping.com/check-id", "start"),
                call("https://hc-ping.com/check-id", "fail"),
            ],
        )


class HealthcheckPingTest(unittest.TestCase):
    def test_ping_failure_does_not_block_job(self):
        with (
            patch(
                "app.subprocess.run",
                side_effect=OSError("curl unavailable"),
            ) as run,
            patch("builtins.print") as print_,
        ):
            app.ping_healthcheck("https://hc-ping.com/check-id", "start")

        run.assert_called_once()
        print_.assert_called_once_with("Healthchecks.io ping failed: curl unavailable")


if __name__ == "__main__":
    unittest.main()
