import unittest
from pathlib import Path
from unittest.mock import patch

import app
import publisher


class FakeS3Client:
    def __init__(self):
        self.uploads = []
        self.puts = []

    def upload_file(self, filename, bucket, key, *, ExtraArgs):
        self.uploads.append((filename, bucket, key, ExtraArgs))

    def put_object(self, **kwargs):
        self.puts.append(kwargs)


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
    def test_publish_mode_dispatches_to_parquet_publisher(self):
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
    def test_build_export_query_uses_stable_ordering(self):
        export = app.ModelExport(
            model="jobs",
            relation="stg_jobs",
            order_by=("organization_slug", "job_slug"),
        )

        self.assertEqual(
            app.build_export_query(export),
            (
                "select * from "
                "`analytics-engineering-jobs.dbt_prd.stg_jobs` "
                "order by `organization_slug`, `job_slug`"
            ),
        )

    def test_r2_store_maps_object_metadata_to_s3_arguments(self):
        client = FakeS3Client()
        store = app.R2Store(client=client, bucket="aej-data")
        metadata = publisher.ObjectMetadata(
            content_type="application/vnd.apache.parquet",
            cache_control="public, max-age=31536000, immutable",
        )

        store.upload_file(
            Path("/tmp/jobs.parquet"),
            "releases/example/jobs.parquet",
            metadata=metadata,
        )

        self.assertEqual(
            client.uploads,
            [
                (
                    "/tmp/jobs.parquet",
                    "aej-data",
                    "releases/example/jobs.parquet",
                    {
                        "ContentType": "application/vnd.apache.parquet",
                        "CacheControl": "public, max-age=31536000, immutable",
                    },
                )
            ],
        )

    def test_r2_store_serializes_json_deterministically(self):
        client = FakeS3Client()
        store = app.R2Store(client=client, bucket="aej-data")
        metadata = publisher.ObjectMetadata(
            content_type="application/json",
            cache_control="no-cache",
        )

        store.put_json(
            "latest.json",
            {"release_id": "release", "schema_version": 1},
            metadata=metadata,
        )

        self.assertEqual(
            client.puts,
            [
                {
                    "Bucket": "aej-data",
                    "Key": "latest.json",
                    "Body": b'{"release_id":"release","schema_version":1}\n',
                    "ContentType": "application/json",
                    "CacheControl": "no-cache",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
