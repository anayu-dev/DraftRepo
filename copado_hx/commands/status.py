from __future__ import annotations

import asyncio
from typing import Optional

import typer

from copado_hx.lib.api import build_api
from copado_hx.lib.config import ConfigManager
from copado_hx.utils.output import print_error, print_json, print_operation, print_operations


app = typer.Typer(help="Inspect Copado deployment and pipeline status.")


@app.command("deployment")
def deployment(
    deployment_id: str = typer.Argument(..., help="Copado deployment ID."),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Show one deployment status."""

    try:
        result = asyncio.run(build_api(ConfigManager(), profile).deployment_status(deployment_id))
    except Exception as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    if json_output:
        print_json(result)
    else:
        print_operation(result)


@app.command("pipeline")
def pipeline(
    story_id: Optional[str] = typer.Option(None, "--story", "-s", help="Filter by user story ID/key."),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Show recent pipeline operations."""

    try:
        results = asyncio.run(build_api(ConfigManager(), profile).pipeline_status(story_id=story_id))
    except Exception as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    if json_output:
        print_json(results)
    else:
        print_operations(results)
