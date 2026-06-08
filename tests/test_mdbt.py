import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent


def load_mdbt_module():
    loader = importlib.machinery.SourceFileLoader("mdbt_script", str(ROOT / "bin/mdbt"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MdbtCommandTest(unittest.TestCase):
    def test_defaults_to_build(self):
        mdbt = load_mdbt_module()

        self.assertEqual(
            mdbt.build_modal_command([], env={}),
            ["uv", "run", "modal", "run", "app.py", "--cmd", "build"],
        )

    def test_preserves_quoted_arguments(self):
        mdbt = load_mdbt_module()

        self.assertEqual(
            mdbt.build_modal_command(
                ["run-operation", "grant_select", "--args", '{"role": "reporter"}'],
                env={},
            ),
            [
                "uv",
                "run",
                "modal",
                "run",
                "app.py",
                "--cmd",
                'run-operation grant_select --args \'{"role": "reporter"}\'',
            ],
        )

    def test_forwards_local_environment_defaults(self):
        mdbt = load_mdbt_module()

        self.assertEqual(
            mdbt.build_modal_command(
                ["run"],
                env={
                    "AEJ_DBT_TARGET": "dev",
                    "AEJ_DBT_USER": "tf",
                    "AEJ_DBT_PR_NUMBER": "123",
                },
            ),
            [
                "uv",
                "run",
                "modal",
                "run",
                "app.py",
                "--cmd",
                "run",
                "--target",
                "dev",
                "--dbt-user",
                "tf",
                "--pr-number",
                "123",
            ],
        )


if __name__ == "__main__":
    unittest.main()
