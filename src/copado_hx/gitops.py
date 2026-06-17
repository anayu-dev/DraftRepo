"""Git command wrappers used by lifecycle automation."""

from __future__ import annotations

from typing import Iterable, Sequence

from .config import HxConfig, existing_paths
from .runner import CommandResult, CommandRunner


class GitCli:
    """Shell-free wrapper around Git commands."""

    def __init__(self, runner: CommandRunner, config: HxConfig) -> None:
        self.runner = runner
        self.config = config

    def status(self, *, short: bool = True) -> CommandResult:
        cmd = ["git", "status"]
        if short:
            cmd.append("--short")
        return self.runner.run(cmd)

    def current_branch(self) -> str:
        result = self.runner.run(["git", "branch", "--show-current"], capture=True)
        return result.stdout.strip()

    def add(self, paths: Sequence[str] = ()) -> CommandResult:
        cmd = ["git", "add"]
        if paths:
            cmd.extend(paths)
        else:
            configured = existing_paths([self.config.source_dir, self.config.manifest])
            cmd.extend(configured or ["."])
        return self.runner.run(cmd)

    def commit(self, message: str) -> CommandResult:
        return self.runner.run(["git", "commit", "-m", message])

    def push(self, *, remote: str | None = None, branch: str | None = None, set_upstream: bool = True) -> CommandResult:
        cmd = ["git", "push"]
        if set_upstream:
            cmd.append("-u")
        cmd.append(remote or self.config.git_remote)
        if branch:
            cmd.append(branch)
        else:
            current = self.current_branch()
            if current:
                cmd.append(current)
        return self.runner.run(cmd)

    def passthrough(self, args: Iterable[str]) -> CommandResult:
        return self.runner.run(["git", *args])
