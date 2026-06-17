"""Copado CLI command wrappers."""

from __future__ import annotations

import shutil
from typing import Iterable, Literal

from .config import HxConfig
from .runner import CommandResult, CommandRunner

SubmitAction = Literal["validate", "promote", "deploy"]
PushStrategy = Literal["full", "scoped"]


class CopadoCli:
    """Thin wrapper around Copado's Salesforce CLI plugin."""

    def __init__(self, runner: CommandRunner, config: HxConfig) -> None:
        self.runner = runner
        self.config = config

    @staticmethod
    def salesforce_cli_installed() -> bool:
        return shutil.which("sf") is not None

    def help(self) -> CommandResult:
        return self.runner.run(["sf", "copado", "--help"], check=False, capture=True)

    def auth_set(self, *, username: str | None = None, alias: str | None = None) -> CommandResult:
        cmd = ["sf", "copado", "auth", "set"]
        if username:
            cmd.extend(["-u", username])
        if alias:
            cmd.extend(["-a", alias])
        return self.runner.run(cmd)

    def auth_get(self, *, json: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "auth", "get"]
        if json:
            cmd.append("--json")
        return self.runner.run(cmd)

    def setup(self, extra_args: Iterable[str] = ()) -> CommandResult:
        return self.runner.run(["sf", "copado", "setup", *extra_args])

    def env_list(self, *, json: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "env", "list"]
        if json:
            cmd.append("--json")
        return self.runner.run(cmd)

    def repo_list(self, *, json: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "repo", "list"]
        if json:
            cmd.append("--json")
        return self.runner.run(cmd)

    def pipeline_list(self, *, json: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "pipeline", "list"]
        if json:
            cmd.append("--json")
        return self.runner.run(cmd)

    def story_list(self, *, listview: str | None = None, query: str | None = None, json: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "story", "list"]
        _extend_option(cmd, "-l", listview)
        _extend_option(cmd, "-q", query)
        if json:
            cmd.append("--json")
        return self.runner.run(cmd)

    def story_set(
        self,
        *,
        story: str | None = None,
        story_id: str | None = None,
        external_id: str | None = None,
        base_branch: str | None = None,
        credential: str | None = None,
        no_auto_detect: bool = True,
    ) -> CommandResult:
        cmd = ["sf", "copado", "story", "set"]
        _extend_option(cmd, "-s", story)
        _extend_option(cmd, "-i", story_id)
        _extend_option(cmd, "-e", external_id)
        _extend_option(cmd, "-b", base_branch or self.config.base_branch)
        _extend_option(cmd, "-c", credential)
        if no_auto_detect:
            cmd.append("--no-auto-detect")
        return self.runner.run(cmd)

    def story_display(self, *, story: str | None = None, story_id: str | None = None, json: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "story", "display"]
        _extend_option(cmd, "-s", story)
        _extend_option(cmd, "-i", story_id)
        if json:
            cmd.append("--json")
        return self.runner.run(cmd)

    def story_open(self) -> CommandResult:
        return self.runner.run(["sf", "copado", "story", "open"])

    def story_push(self, *, force: bool = False, strategy: PushStrategy = "scoped") -> CommandResult:
        cmd = ["sf", "copado", "story", "push", "--strategy", strategy]
        if force:
            cmd.append("--force")
        return self.runner.run(cmd)

    def story_submit(self, *, action: SubmitAction, wait: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "story", "submit"]
        cmd.append({"validate": "-v", "promote": "-p", "deploy": "-d"}[action])
        if wait:
            cmd.append("-w")
        return self.runner.run(cmd)

    def job_get(self, *, job_id: str, json: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "job", "get", "-i", job_id]
        if json:
            cmd.append("--json")
        return self.runner.run(cmd)

    def job_list(self, *, json: bool = False) -> CommandResult:
        cmd = ["sf", "copado", "job", "list"]
        if json:
            cmd.append("--json")
        return self.runner.run(cmd)

    def passthrough(self, args: Iterable[str]) -> CommandResult:
        return self.runner.run(["sf", "copado", *args])


def _extend_option(cmd: list[str], option: str, value: str | None) -> None:
    if value:
        cmd.extend([option, value])
