import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
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


class FakeBigQueryJob:
    def result(self):
        return self


class FakeBigQueryDataset:
    def __init__(self, dataset_id, *, created, modified=None, labels=None):
        self.dataset_id = dataset_id
        self.created = created
        self.modified = modified
        self.labels = labels or {}


class FakeBigQueryTable:
    def __init__(self, table_id):
        self.table_id = table_id
        self.expires = None


class FakeBigQueryClient:
    def __init__(self, *, datasets=(), tables=()):
        self.datasets = {dataset.dataset_id: dataset for dataset in datasets}
        self.tables = {table.table_id: table for table in tables}
        self.deleted_datasets = []
        self.queries = []
        self.updated_datasets = []
        self.updated_tables = []

    def query(self, query):
        self.queries.append(query)
        return FakeBigQueryJob()

    def get_dataset(self, dataset):
        return self.datasets[dataset.rpartition(".")[2]]

    def update_dataset(self, dataset, fields):
        self.updated_datasets.append((dataset, fields))

    def list_datasets(self, *, project):
        self.listed_dataset_project = project
        return self.datasets.values()

    def list_tables(self, dataset):
        self.listed_table_dataset = dataset
        return self.tables.values()

    def get_table(self, table):
        return self.tables[table.rpartition(".")[2]]

    def update_table(self, table, fields):
        self.updated_tables.append((table, fields))

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

        client = object()
        with (
            patch.dict("os.environ", env, clear=True),
            patch("app.subprocess.run") as run,
            patch("app.create_bigquery_client", return_value=client),
            patch("app.configure_ci_dataset") as configure_ci_dataset,
            patch("app.set_ci_relation_expirations") as set_expirations,
        ):
            app.run_dbt.local(cmd="debug", target="ci", pr_number="123")

        run.assert_called_once_with(
            ["dbt", "debug", "--profiles-dir", ".", "--target", "ci"],
            check=True,
            env=env | {"PR_NUMBER": "123"},
        )
        configure_ci_dataset.assert_called_once_with("123", client=client)
        set_expirations.assert_called_once_with("123", client=client)

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


class DbtCiLifecycleTest(unittest.TestCase):
    def test_configures_default_expiration_and_ci_labels(self):
        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        dataset = FakeBigQueryDataset(
            "dbt_ci_123",
            created=now,
            labels={"existing": "label"},
        )
        client = FakeBigQueryClient(datasets=[dataset])

        with patch.dict("os.environ", {"GCP_PROJECT_ID": "configured-project"}):
            app.configure_ci_dataset("123", client=client, now=now)

        self.assertEqual(
            client.queries,
            [
                (
                    "create schema if not exists `configured-project.dbt_ci_123` "
                    'options(location="US", default_table_expiration_days=30)'
                ),
                (
                    "alter schema `configured-project.dbt_ci_123` "
                    "set options(default_table_expiration_days=30)"
                ),
            ],
        )
        self.assertEqual(
            dataset.labels,
            {
                "existing": "label",
                "environment": "ci",
                "managed_by": "aej_dbt",
                "ci_last_used": "20260714t120000z",
            },
        )
        self.assertEqual(client.updated_datasets, [(dataset, ["labels"])])

    def test_sets_expiration_on_existing_ci_relations(self):
        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        tables = [FakeBigQueryTable("model"), FakeBigQueryTable("view")]
        client = FakeBigQueryClient(tables=tables)

        with patch.dict("os.environ", {"GCP_PROJECT_ID": "configured-project"}):
            app.set_ci_relation_expirations("123", client=client, now=now)

        expected_expiration = now + timedelta(days=30)
        self.assertEqual(client.listed_table_dataset, "configured-project.dbt_ci_123")
        self.assertTrue(all(table.expires == expected_expiration for table in tables))
        self.assertEqual(
            client.updated_tables,
            [(tables[0], ["expires"]), (tables[1], ["expires"])],
        )

    def test_deletes_pr_dataset_and_its_contents(self):
        client = FakeBigQueryClient()

        with patch.dict("os.environ", {"GCP_PROJECT_ID": "configured-project"}):
            app.delete_ci_dataset("123", client=client)

        self.assertEqual(
            client.deleted_datasets,
            [("configured-project.dbt_ci_123", True, True)],
        )

    def test_deletes_only_ci_datasets_unused_for_thirty_days(self):
        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        datasets = [
            FakeBigQueryDataset(
                "dbt_ci_100",
                created=datetime(2026, 5, 1, tzinfo=UTC),
                labels={"ci_last_used": "20260501t000000z"},
            ),
            FakeBigQueryDataset(
                "dbt_ci_200",
                created=datetime(2026, 5, 1, tzinfo=UTC),
                labels={"ci_last_used": "20260701t000000z"},
            ),
            FakeBigQueryDataset(
                "dbt_ci_300",
                created=datetime(2026, 5, 1, tzinfo=UTC),
                modified=datetime(2026, 5, 15, tzinfo=UTC),
            ),
            FakeBigQueryDataset(
                "dbt_ci_invalid",
                created=datetime(2026, 5, 1, tzinfo=UTC),
            ),
            FakeBigQueryDataset(
                "dbt_prd",
                created=datetime(2026, 5, 1, tzinfo=UTC),
            ),
        ]
        client = FakeBigQueryClient(datasets=datasets)

        with patch.dict("os.environ", {"GCP_PROJECT_ID": "configured-project"}):
            deleted = app.delete_stale_ci_datasets(client=client, now=now)

        self.assertEqual(deleted, ["dbt_ci_100", "dbt_ci_300"])
        self.assertEqual(client.listed_dataset_project, "configured-project")
        self.assertEqual(
            client.deleted_datasets,
            [
                ("configured-project.dbt_ci_100", True, True),
                ("configured-project.dbt_ci_300", True, True),
            ],
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
