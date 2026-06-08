import unittest
from unittest.mock import patch

import app


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


if __name__ == "__main__":
    unittest.main()
