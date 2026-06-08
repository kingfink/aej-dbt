import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent


def load_mpub_module():
    loader = importlib.machinery.SourceFileLoader(
        "mpub_script",
        str(ROOT / "bin/mpub"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MpubCommandTest(unittest.TestCase):
    def test_builds_modal_publish_command(self):
        mpub = load_mpub_module()

        self.assertEqual(
            mpub.build_modal_command(),
            ["uv", "run", "modal", "run", "app.py", "--publish"],
        )


if __name__ == "__main__":
    unittest.main()
