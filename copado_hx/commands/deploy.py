from __future__ import annotations

import asyncio
from typing import Optional

import questionary
import typer

from copado_hx.lib.api import build_api
from copado_hx.lib.config import ConfigManager
from copado_hx.utils.output import print_error, print_json, print_operation, print_warning


app = typer.Typer(help="Validate and deploy Copado user stories.")

PRODUCTION_ALIASES = {"prod", "production"}
PRODUCTION_CONFIRMATION_PHRASE = "DEPLOY TO PRODUCTION"


class ProductionDeploymentRefused(RuntimeError):
    """Raised when the required production confirmation is missing."""


@app.command()
def validate(
    story_id: str = typer.Argument(..., help="User story ID/key."),
    target: str = typer.Option(..., "--target", "-t", help="Target environment."),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Validate a user story deployment."""

    try:
        result = asyncio.run(
            build_api(ConfigManager(), profile).validate_story(
                story_id,
                target_environment=target,
            )
        )
    except Exception as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    if json_output:
        print_json(result)
    else:
        print_operation(result)


@app.command("story")
def deploy_story(
    story_id: str = typer.Argument(..., help="User story ID/key."),
    target: str = typer.Option(..., "--target", "-t", help="Target environment."),
    deployment_id: Optional[str] = typer.Option(
        None,
        "--deployment-id",
        help="Existing Copado deployment ID to execute.",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Deploy a user story.

    Production targets always require typing the exact confirmation phrase.
    There is intentionally no --yes or environment variable bypass.
    """

    try:
        require_production_confirmation(target)
        result = asyncio.run(
            build_api(ConfigManager(), profile).deploy_story(
                story_id,
                target_environment=target,
                deployment_id=deployment_id,
            )
        )
    except Exception as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    if json_output:
        print_json(result)
    else:
        print_operation(result)


def is_production_environment(environment: str) -> bool:
    return environment.strip().lower() in PRODUCTION_ALIASES


def require_production_confirmation(environment: str) -> None:
    if not is_production_environment(environment):
        return
    print_warning("Production deployment requested.")
    confirmation = questionary.text(
        f"Type '{PRODUCTION_CONFIRMATION_PHRASE}' to continue:",
        default="",
    ).ask()
    ensure_production_confirmation(environment, confirmation)


def ensure_production_confirmation(environment: str, confirmation: Optional[str]) -> None:
    if not is_production_environment(environment):
        return
    if confirmation != PRODUCTION_CONFIRMATION_PHRASE:
        raise ProductionDeploymentRefused(
            "Production deployment cancelled. Exact human confirmation is required."
        )
