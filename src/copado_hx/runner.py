"""External command execution helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Mapping, Sequence, TextIO

from .errors import CommandExecutionError


@dataclass(frozen=True)
class CommandResult:
    """Result from a command executed by :class:`CommandRunner`."""

    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""


class CommandRunner:
    """Run shell-free subprocess commands with optional dry-run output."""

    def __init__(
        self,
        *,
        dry_run: bool = False,
        verbose: bool = False,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.verbose = verbose
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr

    def run(
        self,
        args: Sequence[str | os.PathLike[str]],
        *,
        cwd: str | os.PathLike[str] | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = True,
        capture: bool = False,
        input_text: str | None = None,
    ) -> CommandResult:
        """Execute a command and return its result.

        Args are passed directly to ``subprocess.run`` without a shell. In dry-run
        mode the command is printed and a successful empty result is returned.
        """

        rendered_args = [str(arg) for arg in args]
        if self.dry_run:
            print(f"+ {format_command(rendered_args)}", file=self.stdout)
            return CommandResult(rendered_args, 0)

        if self.verbose:
            print(f"+ {format_command(rendered_args)}", file=self.stderr)

        completed = subprocess.run(
            rendered_args,
            cwd=Path(cwd) if cwd is not None else None,
            env={**os.environ, **env} if env else None,
            input=input_text,
            text=True,
            capture_output=capture,
            check=False,
        )
        result = CommandResult(
            rendered_args,
            completed.returncode,
            completed.stdout or "",
            completed.stderr or "",
        )
        if check and result.returncode != 0:
            raise CommandExecutionError(result.args, result.returncode, result.stdout, result.stderr)
        return result


def format_command(args: Sequence[str]) -> str:
    """Return a shell-displayable command line."""

    return " ".join(shlex.quote(str(arg)) for arg in args)
