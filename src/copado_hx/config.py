"""Configuration loading and writing for Copado HX."""

from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

from .errors import CopadoHxError

DEFAULT_CONFIG_NAME = ".copado-hx.ini"


@dataclass(frozen=True)
class HxConfig:
    """Project-level Copado HX settings."""

    source_dir: str = "force-app"
    mdapi_dir: str = "mdapi"
    manifest: str = "manifest/package.xml"
    target_org: str = ""
    test_level: str = "RunLocalTests"
    wait_minutes: int = 60
    copado_username: str = ""
    user_story: str = ""
    base_branch: str = "main"
    git_remote: str = "origin"

    @classmethod
    def from_parser(cls, parser: ConfigParser) -> "HxConfig":
        return cls(
            source_dir=_get(parser, "project", "source_dir", cls.source_dir),
            mdapi_dir=_get(parser, "project", "mdapi_dir", cls.mdapi_dir),
            manifest=_get(parser, "project", "manifest", cls.manifest),
            target_org=_env("COPADO_HX_TARGET_ORG", _get(parser, "salesforce", "target_org", "")),
            test_level=_get(parser, "salesforce", "test_level", cls.test_level),
            wait_minutes=_get_int(parser, "salesforce", "wait_minutes", cls.wait_minutes),
            copado_username=_env(
                "COPADO_HX_COPADO_USERNAME",
                _get(parser, "copado", "username", ""),
            ),
            user_story=_env("COPADO_HX_USER_STORY", _get(parser, "copado", "user_story", "")),
            base_branch=_get(parser, "copado", "base_branch", cls.base_branch),
            git_remote=_get(parser, "git", "remote", cls.git_remote),
        )

    def to_parser(self) -> ConfigParser:
        parser = ConfigParser()
        parser["project"] = {
            "source_dir": self.source_dir,
            "mdapi_dir": self.mdapi_dir,
            "manifest": self.manifest,
        }
        parser["salesforce"] = {
            "target_org": self.target_org,
            "test_level": self.test_level,
            "wait_minutes": str(self.wait_minutes),
        }
        parser["copado"] = {
            "username": self.copado_username,
            "user_story": self.user_story,
            "base_branch": self.base_branch,
        }
        parser["git"] = {"remote": self.git_remote}
        return parser


def find_config(start: Path | None = None) -> Path | None:
    """Find the nearest Copado HX config file walking upward from ``start``."""

    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / DEFAULT_CONFIG_NAME
        if candidate.exists():
            return candidate
    return None


def load_config(path: str | os.PathLike[str] | None = None) -> tuple[HxConfig, Path | None]:
    """Load configuration from a path or the nearest project config."""

    config_path = Path(path).expanduser().resolve() if path else find_config()
    parser = ConfigParser()
    if config_path:
        if not config_path.exists():
            raise CopadoHxError(f"Config file does not exist: {config_path}")
        parser.read(config_path)
    return HxConfig.from_parser(parser), config_path


def write_default_config(
    path: str | os.PathLike[str] | None = None,
    *,
    overwrite: bool = False,
    source_dir: str = "force-app",
    target_org: str = "",
    copado_username: str = "",
    user_story: str = "",
    base_branch: str = "main",
) -> Path:
    """Write a starter config file and return its path."""

    config_path = Path(path or DEFAULT_CONFIG_NAME).expanduser()
    if config_path.exists() and not overwrite:
        raise CopadoHxError(f"Config already exists: {config_path}. Use --force to overwrite.")

    config = HxConfig(
        source_dir=source_dir,
        target_org=target_org,
        copado_username=copado_username,
        user_story=user_story,
        base_branch=base_branch,
    )
    parser = config.to_parser()
    with config_path.open("w", encoding="utf-8") as handle:
        handle.write("# Copado HX project configuration\n")
        handle.write("# Values can be overridden with COPADO_HX_TARGET_ORG,\n")
        handle.write("# COPADO_HX_COPADO_USERNAME, and COPADO_HX_USER_STORY.\n\n")
        parser.write(handle)
    return config_path


def require_value(name: str, explicit: str | None, configured: str) -> str:
    """Return an explicit/configured value or raise a helpful error."""

    value = explicit or configured
    if not value:
        raise CopadoHxError(f"Missing required value for {name}. Provide the flag or configure it.")
    return value


def existing_paths(paths: Iterable[str]) -> list[str]:
    """Return configured paths that currently exist."""

    return [path for path in paths if path and Path(path).exists()]


def _get(parser: ConfigParser, section: str, option: str, default: str) -> str:
    if parser.has_option(section, option):
        return parser.get(section, option).strip()
    return default


def _get_int(parser: ConfigParser, section: str, option: str, default: int) -> int:
    if not parser.has_option(section, option):
        return default
    try:
        return parser.getint(section, option)
    except ValueError as exc:
        raise CopadoHxError(f"Config value [{section}] {option} must be an integer.") from exc


def _env(name: str, fallback: str) -> str:
    return os.getenv(name, fallback).strip()
