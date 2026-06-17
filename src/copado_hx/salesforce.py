"""Salesforce CLI command wrappers."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Iterable, Sequence

from .config import HxConfig
from .runner import CommandResult, CommandRunner


class SalesforceCli:
    """Thin wrapper around the Salesforce ``sf`` executable."""

    def __init__(self, runner: CommandRunner, config: HxConfig) -> None:
        self.runner = runner
        self.config = config

    @staticmethod
    def installed() -> bool:
        return shutil.which("sf") is not None

    def version(self) -> CommandResult:
        return self.runner.run(["sf", "--version"], check=False, capture=True)

    def plugin_install_copado(self) -> CommandResult:
        return self.runner.run(["sf", "plugins", "install", "@copado/copado-cli"])

    def org_list(self, *, all_orgs: bool = False) -> CommandResult:
        cmd = ["sf", "org", "list"]
        if all_orgs:
            cmd.append("--all")
        return self.runner.run(cmd)

    def login_jwt(
        self,
        *,
        username: str,
        client_id: str,
        jwt_key_file: str,
        instance_url: str | None = None,
        alias: str | None = None,
        set_default: bool = False,
    ) -> CommandResult:
        cmd = [
            "sf",
            "org",
            "login",
            "jwt",
            "--username",
            username,
            "--client-id",
            client_id,
            "--jwt-key-file",
            jwt_key_file,
            "--no-prompt",
        ]
        _extend_option(cmd, "--instance-url", instance_url)
        _extend_option(cmd, "--alias", alias)
        if set_default:
            cmd.append("--set-default")
        return self.runner.run(cmd)

    def set_default_org(self, target_org: str) -> CommandResult:
        return self.runner.run(["sf", "config", "set", f"target-org={target_org}"])

    def retrieve(
        self,
        *,
        target_org: str | None = None,
        source_dir: str | None = None,
        manifest: str | None = None,
        metadata: Sequence[str] = (),
        wait_minutes: int | None = None,
    ) -> CommandResult:
        cmd = ["sf", "project", "retrieve", "start"]
        self._target(cmd, target_org)
        _extend_option(cmd, "--wait", str(wait_minutes or self.config.wait_minutes))
        if manifest:
            _extend_option(cmd, "--manifest", manifest)
        elif metadata:
            for item in metadata:
                _extend_option(cmd, "--metadata", item)
        else:
            _extend_option(cmd, "--source-dir", source_dir or self.config.source_dir)
        return self.runner.run(cmd)

    def deploy(
        self,
        *,
        validate_only: bool = False,
        target_org: str | None = None,
        source_dir: str | None = None,
        manifest: str | None = None,
        test_level: str | None = None,
        tests: Sequence[str] = (),
        wait_minutes: int | None = None,
        ignore_conflicts: bool = False,
    ) -> CommandResult:
        cmd = ["sf", "project", "deploy", "validate" if validate_only else "start"]
        self._target(cmd, target_org)
        if manifest:
            _extend_option(cmd, "--manifest", manifest)
        else:
            _extend_option(cmd, "--source-dir", source_dir or self.config.source_dir)
        _extend_option(cmd, "--test-level", test_level or self.config.test_level)
        for test in tests:
            _extend_option(cmd, "--tests", test)
        _extend_option(cmd, "--wait", str(wait_minutes or self.config.wait_minutes))
        if ignore_conflicts:
            cmd.append("--ignore-conflicts")
        return self.runner.run(cmd)

    def quick_deploy(self, *, job_id: str, target_org: str | None = None, wait_minutes: int | None = None) -> CommandResult:
        cmd = ["sf", "project", "deploy", "quick", "--job-id", job_id]
        self._target(cmd, target_org)
        _extend_option(cmd, "--wait", str(wait_minutes or self.config.wait_minutes))
        return self.runner.run(cmd)

    def preview(self, *, target_org: str | None = None, source_dir: str | None = None) -> CommandResult:
        cmd = ["sf", "project", "deploy", "preview"]
        self._target(cmd, target_org)
        _extend_option(cmd, "--source-dir", source_dir or self.config.source_dir)
        return self.runner.run(cmd)

    def convert_source(self, *, root_dir: str | None = None, output_dir: str | None = None) -> CommandResult:
        return self.runner.run(
            [
                "sf",
                "project",
                "convert",
                "source",
                "--root-dir",
                root_dir or self.config.source_dir,
                "--output-dir",
                output_dir or self.config.mdapi_dir,
            ]
        )

    def convert_mdapi(self, *, root_dir: str | None = None, output_dir: str | None = None) -> CommandResult:
        return self.runner.run(
            [
                "sf",
                "project",
                "convert",
                "mdapi",
                "--root-dir",
                root_dir or self.config.mdapi_dir,
                "--output-dir",
                output_dir or self.config.source_dir,
            ]
        )

    def passthrough(self, args: Iterable[str]) -> CommandResult:
        return self.runner.run(["sf", *args])

    def _target(self, cmd: list[str], target_org: str | None) -> None:
        org = target_org or self.config.target_org
        _extend_option(cmd, "--target-org", org or None)


def ensure_salesforce_project() -> bool:
    """Return whether the current directory looks like an SF project."""

    return Path("sfdx-project.json").exists()


def _extend_option(cmd: list[str], option: str, value: str | None) -> None:
    if value:
        cmd.extend([option, value])
