import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent


def load_mpublish_module():
    loader = importlib.machinery.SourceFileLoader(
        "mpublish_script",
        str(ROOT / "bin/mpublish"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MpublishCommandTest(unittest.TestCase):
    def test_builds_modal_publish_command(self):
        mpublish = load_mpublish_module()

        self.assertEqual(
            mpublish.build_modal_command(),
            ["uv", "run", "modal", "run", "app.py", "--publish"],
        )


if __name__ == "__main__":
    unittest.main()
