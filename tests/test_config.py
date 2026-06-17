from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copado_hx.config import load_config, write_default_config


class ConfigTests(unittest.TestCase):
    def test_write_and_load_config(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".copado-hx.ini"
            write_default_config(
                path,
                source_dir="force-app",
                target_org="dev",
                copado_username="copado@example.com",
                user_story="US-001",
                base_branch="main",
            )

            config, loaded_path = load_config(path)

            self.assertEqual(path.resolve(), loaded_path)
            self.assertEqual("force-app", config.source_dir)
            self.assertEqual("dev", config.target_org)
            self.assertEqual("copado@example.com", config.copado_username)
            self.assertEqual("US-001", config.user_story)

    def test_environment_overrides(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".copado-hx.ini"
            write_default_config(path, target_org="configured")
            previous = os.environ.get("COPADO_HX_TARGET_ORG")
            os.environ["COPADO_HX_TARGET_ORG"] = "from-env"
            try:
                config, _ = load_config(path)
            finally:
                if previous is None:
                    os.environ.pop("COPADO_HX_TARGET_ORG", None)
                else:
                    os.environ["COPADO_HX_TARGET_ORG"] = previous

            self.assertEqual("from-env", config.target_org)


if __name__ == "__main__":
    unittest.main()
