from __future__ import annotations

import asyncio
from typing import Optional

import typer

from copado_hx.lib.api import build_api
from copado_hx.lib.config import ConfigManager
from copado_hx.utils.output import print_error, print_json, print_operation


app = typer.Typer(help="Promote Copado user stories between pipeline environments.")


@app.command()
def story(
    story_id: str = typer.Argument(..., help="User story ID/key."),
    target: str = typer.Option(..., "--target", "-t", help="Target environment."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate promotion without changing state."),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Promote a user story."""

    try:
        result = asyncio.run(
            build_api(ConfigManager(), profile).promote_story(
                story_id,
                target_environment=target,
                dry_run=dry_run,
            )
        )
    except Exception as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    if json_output:
        print_json(result)
    else:
        print_operation(result)
