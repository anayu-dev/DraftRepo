from __future__ import annotations

import asyncio
from typing import Optional

import typer

from copado_hx.lib.api import build_api
from copado_hx.lib.config import ConfigManager, ConfigurationError
from copado_hx.utils.output import print_error, print_json, print_story, print_story_table


app = typer.Typer(help="Pull and inspect Copado user stories from the terminal.")


@app.command("list")
def list_stories(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by story status."),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """List Copado user stories."""

    try:
        stories = asyncio.run(build_api(ConfigManager(), profile).list_stories(status=status))
    except Exception as exc:
        _exit(exc)
    if json_output:
        print_json(stories)
    else:
        print_story_table(stories)


@app.command("show")
def show_story(
    story_id: str = typer.Argument(..., help="User story ID/key."),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Show one Copado user story."""

    try:
        story = asyncio.run(build_api(ConfigManager(), profile).get_story(story_id))
    except Exception as exc:
        _exit(exc)
    if json_output:
        print_json(story)
    else:
        print_story(story)


def _exit(exc: Exception) -> None:
    if isinstance(exc, ConfigurationError):
        print_error(str(exc))
    else:
        print_error(str(exc))
    raise typer.Exit(1) from exc
