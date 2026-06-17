from __future__ import annotations

import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Sequence
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copado_hx.cli import main
from copado_hx.config import write_default_config
from copado_hx.runner import CommandResult, CommandRunner


class RecordingRunner(CommandRunner):
    def __init__(self) -> None:
        super().__init__()
        self.commands: list[list[str]] = []

    def run(self, args: Sequence[str | object], **kwargs: object) -> CommandResult:
        rendered = [str(arg) for arg in args]
        self.commands.append(rendered)
        if rendered == ["git", "branch", "--show-current"]:
            return CommandResult(rendered, 0, stdout="feature/US-001\n")
        if rendered == ["sf", "--version"]:
            return CommandResult(rendered, 0, stdout="sf/2.0.0\n")
        if rendered == ["sf", "copado", "--help"]:
            return CommandResult(rendered, 0, stdout="Copado help\n")
        return CommandResult(rendered, 0)


class CliTests(unittest.TestCase):
    def test_story_set_command(self) -> None:
        with configured_project() as config:
            runner = RecordingRunner()
            code = main(
                ["--config", str(config), "story", "set", "--story", "US-001", "--base-branch", "main"],
                runner=runner,
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        self.assertEqual(0, code)
        self.assertEqual(
            [["sf", "copado", "story", "set", "-s", "US-001", "-b", "main", "--no-auto-detect"]],
            runner.commands,
        )

    def test_story_submit_command(self) -> None:
        with configured_project() as config:
            runner = RecordingRunner()
            code = main(
                ["--config", str(config), "story", "submit", "--deploy", "--wait"],
                runner=runner,
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        self.assertEqual(0, code)
        self.assertEqual([["sf", "copado", "story", "submit", "-d", "-w"]], runner.commands)

    def test_sf_validate_command(self) -> None:
        with configured_project() as config:
            runner = RecordingRunner()
            code = main(
                [
                    "--config",
                    str(config),
                    "sf",
                    "validate",
                    "--target-org",
                    "dev",
                    "--source-dir",
                    "force-app",
                    "--test-level",
                    "RunSpecifiedTests",
                    "--test",
                    "AccountTest",
                    "--wait",
                    "15",
                ],
                runner=runner,
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        self.assertEqual(0, code)
        self.assertEqual(
            [
                [
                    "sf",
                    "project",
                    "deploy",
                    "validate",
                    "--target-org",
                    "dev",
                    "--source-dir",
                    "force-app",
                    "--test-level",
                    "RunSpecifiedTests",
                    "--tests",
                    "AccountTest",
                    "--wait",
                    "15",
                ]
            ],
            runner.commands,
        )

    def test_lifecycle_run_sequence(self) -> None:
        with configured_project() as config:
            runner = RecordingRunner()
            code = main(
                [
                    "--config",
                    str(config),
                    "lifecycle",
                    "run",
                    "--story",
                    "US-001",
                    "--target-org",
                    "dev",
                    "--retrieve",
                    "--message",
                    "US-001 change",
                    "--path",
                    "force-app",
                    "--submit-validate",
                    "--wait",
                ],
                runner=runner,
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        self.assertEqual(0, code)
        self.assertEqual(
            [
                ["sf", "copado", "story", "set", "-s", "US-001", "-b", "main", "--no-auto-detect"],
                [
                    "sf",
                    "project",
                    "retrieve",
                    "start",
                    "--target-org",
                    "dev",
                    "--wait",
                    "60",
                    "--source-dir",
                    "force-app",
                ],
                [
                    "sf",
                    "project",
                    "deploy",
                    "validate",
                    "--target-org",
                    "dev",
                    "--source-dir",
                    "force-app",
                    "--test-level",
                    "RunLocalTests",
                    "--wait",
                    "60",
                ],
                ["git", "add", "force-app"],
                ["git", "commit", "-m", "US-001 change"],
                ["git", "branch", "--show-current"],
                ["git", "push", "-u", "origin", "feature/US-001"],
                ["sf", "copado", "story", "push", "--strategy", "scoped"],
                ["sf", "copado", "story", "submit", "-v", "-w"],
            ],
            runner.commands,
        )

    def test_raw_passthrough_strips_separator(self) -> None:
        with configured_project() as config:
            runner = RecordingRunner()
            code = main(
                ["--config", str(config), "copado", "raw", "--", "package", "list"],
                runner=runner,
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        self.assertEqual(0, code)
        self.assertEqual([["sf", "copado", "package", "list"]], runner.commands)


class configured_project:
    def __enter__(self) -> Path:
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".copado-hx.ini"
        write_default_config(
            self.path,
            source_dir="force-app",
            target_org="dev",
            copado_username="copado@example.com",
            user_story="US-DEFAULT",
            base_branch="main",
        )
        return self.path

    def __exit__(self, *exc: object) -> None:
        self.tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
