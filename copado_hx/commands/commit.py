from __future__ import annotations

import asyncio
from typing import Optional

import questionary
import typer

from copado_hx.lib.api import build_api
from copado_hx.lib.config import ConfigManager
from copado_hx.utils.output import print_error, print_json, print_operation


app = typer.Typer(help="Commit Copado user stories.")


@app.command()
def story(
    story_id: str = typer.Argument(..., help="User story ID/key."),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Commit message."),
    include_metadata: bool = typer.Option(
        True,
        "--include-metadata/--no-include-metadata",
        help="Include metadata changes in the commit.",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Commit a user story through the Copado CI/CD Actions API."""

    message = message or questionary.text("Commit message:").ask()
    if not message:
        print_error("commit message is required")
        raise typer.Exit(1)
    try:
        result = asyncio.run(
            build_api(ConfigManager(), profile).commit_story(
                story_id,
                message=message,
                include_metadata=include_metadata,
            )
        )
    except Exception as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    if json_output:
        print_json(result)
    else:
        print_operation(result)
