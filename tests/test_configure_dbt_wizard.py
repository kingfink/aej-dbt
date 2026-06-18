import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIGURE_SCRIPT = REPO_ROOT / "scripts" / "configure-dbt-wizard"


class ConfigureDbtWizardTest(unittest.TestCase):
    def test_missing_provider_key_reports_documented_byok_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "home"
            bin_dir = Path(temp_dir) / "bin"
            home.mkdir()
            bin_dir.mkdir()

            wizard = bin_dir / "wizard"
            wizard.write_text("#!/usr/bin/env bash\nexit 0\n")
            wizard.chmod(0o755)

            env = os.environ.copy()
            env.update({"HOME": str(home), "PATH": f"{bin_dir}:{env['PATH']}"})
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("OPENAI_API_KEY", None)
            env.pop("DBT_WIZARD_API_KEY", None)

            result = subprocess.run(
                [str(CONFIGURE_SCRIPT), str(REPO_ROOT)],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertIn("ANTHROPIC_API_KEY or OPENAI_API_KEY", result.stderr)
            self.assertNotIn("DBT_WIZARD_API_KEY", result.stderr)


if __name__ == "__main__":
    unittest.main()
