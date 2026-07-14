import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import call, patch

import app


class FakeGCSBlob:
    def __init__(self):
        self.cache_control = None
        self.uploads = []

    def upload_from_filename(self, filename, *, content_type):
        self.uploads.append((filename, content_type))


class FakeGCSBucket:
    def __init__(self):
        self.blobs = {}

    def blob(self, name):
        return self.blobs.setdefault(name, FakeGCSBlob())


class FakeGCSClient:
    def __init__(self):
        self.buckets = {}

    def bucket(self, name):
        return self.buckets.setdefault(name, FakeGCSBucket())


class FakeBigQueryClient:
    def __init__(self):
        self.deleted_datasets = []

    def delete_dataset(self, dataset, *, delete_contents, not_found_ok):
        self.deleted_datasets.append((dataset, delete_contents, not_found_ok))


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

    def test_rejects_non_numeric_pr_number(self):
        with self.assertRaisesRegex(ValueError, "only digits"):
            app.dbt_env("ci", pr_number="feature-123")


class AppDispatchTest(unittest.TestCase):
    def test_publish_mode_dispatches_to_parquet_publish_job(self):
        with (
            patch("app.run_dbt.remote") as run_dbt,
            patch("app.publish_parquet.remote") as publish_parquet,
        ):
            app.dispatch(publish=True)

        publish_parquet.assert_called_once_with()
        run_dbt.assert_not_called()

    def test_cleanup_mode_dispatches_to_ci_cleanup_job(self):
        with (
            patch("app.run_dbt.remote") as run_dbt,
            patch("app.publish_parquet.remote") as publish_parquet,
            patch("app.cleanup_ci_dataset.remote") as cleanup_ci_dataset,
        ):
            app.dispatch(cleanup_ci=True, pr_number="123")

        cleanup_ci_dataset.assert_called_once_with("123")
        publish_parquet.assert_not_called()
        run_dbt.assert_not_called()

    def test_rejects_multiple_dispatch_modes(self):
        with self.assertRaisesRegex(ValueError, "cannot be used together"):
            app.dispatch(publish=True, cleanup_ci=True)


class DbtCiCleanupTest(unittest.TestCase):
    def test_deletes_pr_dataset_and_its_contents(self):
        client = FakeBigQueryClient()

        with patch.dict("os.environ", {"GCP_PROJECT_ID": "configured-project"}):
            app.delete_ci_dataset("123", client=client)

        self.assertEqual(
            client.deleted_datasets,
            [("configured-project.dbt_ci_123", True, True)],
        )


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
        client = FakeGCSClient()

        app.upload_parquet_files(
            client=client,
            bucket_name="aej-data",
            paths=[Path("/tmp/jobs.parquet")],
        )

        blob = client.buckets["aej-data"].blobs["jobs.parquet"]
        self.assertEqual(blob.cache_control, "no-cache")
        self.assertEqual(
            blob.uploads,
            [
                (
                    "/tmp/jobs.parquet",
                    "application/vnd.apache.parquet",
                ),
            ],
        )


class ShouldFullRefreshTest(unittest.TestCase):
    def test_sunday_with_stale_marker_triggers_full_refresh(self):
        sunday = datetime(2026, 6, 14, 0, 0, tzinfo=UTC)

        self.assertTrue(app.should_full_refresh(sunday, "2026-06-07"))

    def test_sunday_without_marker_triggers_full_refresh(self):
        sunday = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)

        self.assertTrue(app.should_full_refresh(sunday, ""))

    def test_sunday_already_claimed_stays_incremental(self):
        sunday = datetime(2026, 6, 14, 18, 0, tzinfo=UTC)

        self.assertFalse(app.should_full_refresh(sunday, "2026-06-14"))

    def test_other_weekdays_stay_incremental(self):
        for label, moment in [
            ("saturday", datetime(2026, 6, 13, 0, 0, tzinfo=UTC)),
            ("monday", datetime(2026, 6, 15, 0, 0, tzinfo=UTC)),
        ]:
            with self.subTest(weekday=label):
                self.assertFalse(app.should_full_refresh(moment, "2026-06-07"))


class ScheduledProductionSyncTest(unittest.TestCase):
    def test_runs_incremental_then_publish_and_reports_success(self):
        env = {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/check-id"}
        events = []

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.state", {}) as state,
            patch("app.should_full_refresh", return_value=False),
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
                ("dbt", {"cmd": "build", "target": "prd"}),
                ("publish",),
                ("ping", ""),
            ],
        )
        self.assertEqual(state, {})

    def test_full_refresh_run_claims_the_day_and_passes_flag(self):
        env = {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/check-id"}
        state = {"last_full_refresh": "2026-06-07"}
        sunday = datetime(2026, 6, 14, 0, 0, tzinfo=UTC)

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.state", state),
            patch("app.datetime") as clock,
            patch("app.should_full_refresh", return_value=True),
            patch("app.ping_healthcheck"),
            patch("app.execute_dbt") as execute_dbt,
            patch("app.execute_parquet_publish"),
        ):
            clock.now.return_value = sunday
            app.scheduled_production_sync.local()

        execute_dbt.assert_called_once_with(cmd="build --full-refresh", target="prd")
        self.assertEqual(state, {"last_full_refresh": "2026-06-14"})

    def test_full_refresh_failure_releases_the_claim(self):
        env = {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/check-id"}
        state = {"last_full_refresh": "2026-06-07"}
        sunday = datetime(2026, 6, 14, 0, 0, tzinfo=UTC)
        dbt_error = subprocess.CalledProcessError(1, ["dbt", "build"])

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.state", state),
            patch("app.datetime") as clock,
            patch("app.should_full_refresh", return_value=True),
            patch("app.ping_healthcheck") as ping_healthcheck,
            patch("app.execute_dbt", side_effect=dbt_error),
            patch("app.execute_parquet_publish") as publish,
            self.assertRaises(subprocess.CalledProcessError),
        ):
            clock.now.return_value = sunday
            app.scheduled_production_sync.local()

        publish.assert_not_called()
        self.assertEqual(state, {"last_full_refresh": "2026-06-07"})
        self.assertEqual(
            ping_healthcheck.call_args_list,
            [
                call("https://hc-ping.com/check-id", "start"),
                call("https://hc-ping.com/check-id", "fail"),
            ],
        )

    def test_dbt_failure_reports_failure_without_publishing(self):
        env = {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/check-id"}
        dbt_error = subprocess.CalledProcessError(1, ["dbt", "build"])

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.state", {}),
            patch("app.should_full_refresh", return_value=False),
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
        env = {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/check-id"}
        publish_error = RuntimeError("GCS upload failed")

        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.state", {}),
            patch("app.should_full_refresh", return_value=False),
            patch("app.ping_healthcheck") as ping_healthcheck,
            patch("app.execute_dbt") as execute_dbt,
            patch("app.execute_parquet_publish", side_effect=publish_error),
            self.assertRaisesRegex(RuntimeError, "GCS upload failed"),
        ):
            app.scheduled_production_sync.local()

        execute_dbt.assert_called_once_with(cmd="build", target="prd")
        self.assertEqual(
            ping_healthcheck.call_args_list,
            [
                call("https://hc-ping.com/check-id", "start"),
                call("https://hc-ping.com/check-id", "fail"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
