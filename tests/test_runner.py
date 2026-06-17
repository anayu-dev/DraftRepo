from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copado_hx.runner import CommandRunner, format_command


class RunnerTests(unittest.TestCase):
    def test_dry_run_prints_quoted_command(self) -> None:
        out = io.StringIO()
        runner = CommandRunner(dry_run=True, stdout=out)

        result = runner.run(["sf", "project", "deploy", "start", "--source-dir", "force app"])

        self.assertEqual(0, result.returncode)
        self.assertEqual("+ sf project deploy start --source-dir 'force app'\n", out.getvalue())

    def test_format_command_quotes_spaces(self) -> None:
        self.assertEqual("git commit -m 'hello world'", format_command(["git", "commit", "-m", "hello world"]))


if __name__ == "__main__":
    unittest.main()
