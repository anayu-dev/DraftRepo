"""Exception types used by Copado HX."""

from __future__ import annotations


class CopadoHxError(Exception):
    """Base class for user-facing CLI errors."""


class CommandExecutionError(CopadoHxError):
    """Raised when an external command exits with a non-zero status."""

    def __init__(self, args: list[str], returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.args_list = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        rendered = " ".join(args)
        message = f"Command failed with exit code {returncode}: {rendered}"
        if stderr.strip():
            message = f"{message}\n{stderr.strip()}"
        super().__init__(message)
