from __future__ import annotations

from typing import Optional

import questionary
import typer
from rich.table import Table

from copado_hx.lib.config import ConfigManager, ConfigurationError, CopadoProfile
from copado_hx.utils.output import console, print_error, print_success


app = typer.Typer(help="Manage Copado API profiles without opening a browser.")


@app.command()
def login(
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name."),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Copado API base URL."),
    api_token: Optional[str] = typer.Option(None, "--api-token", help="Copado API token."),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Copado username."),
    org_id: Optional[str] = typer.Option(None, "--org-id", help="Salesforce org ID."),
    demo: bool = typer.Option(False, "--demo", help="Create a mock API demo profile."),
    activate: bool = typer.Option(True, "--activate/--no-activate", help="Make this profile active."),
) -> None:
    """Create or update a profile.

    Authentication is token based and intentionally browserless. Omitted values
    are requested through terminal prompts.
    """

    if demo:
        copado_profile = CopadoProfile(name=profile, demo=True)
        ConfigManager().save_profile(copado_profile, make_active=activate)
        print_success(f"Demo profile '{profile}' saved.")
        return

    base_url = base_url or questionary.text("Copado API base URL:").ask()
    api_token = api_token or questionary.password("Copado API token:").ask()
    username = username or questionary.text("Copado username:", default="").ask()
    if not base_url or not api_token:
        print_error("base URL and API token are required")
        raise typer.Exit(1)

    copado_profile = CopadoProfile(
        name=profile,
        base_url=base_url,
        username=username or None,
        org_id=org_id,
    )
    ConfigManager().save_profile(copado_profile, api_token=api_token, make_active=activate)
    print_success(f"Profile '{profile}' saved.")


@app.command("use")
def use_profile(
    profile: str = typer.Argument(..., help="Profile name to activate."),
) -> None:
    """Switch the active profile."""

    try:
        ConfigManager().set_active_profile(profile)
    except ConfigurationError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    print_success(f"Active profile set to '{profile}'.")


@app.command()
def profiles() -> None:
    """List configured profiles."""

    manager = ConfigManager()
    metadata = manager.load()
    table = Table(title="copado-hx profiles")
    table.add_column("Active")
    table.add_column("Name", style="cyan")
    table.add_column("Mode")
    table.add_column("Base URL")
    table.add_column("Username")
    for profile in manager.list_profiles():
        table.add_row(
            "*" if metadata.active_profile == profile.name else "",
            profile.name,
            "demo" if profile.demo else "api",
            profile.base_url,
            profile.username or "-",
        )
    console.print(table)


@app.command()
def status() -> None:
    """Show the active profile and config location."""

    manager = ConfigManager()
    try:
        profile = manager.get_profile()
    except ConfigurationError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    table = Table(title="copado-hx auth status")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("active_profile", profile.name)
    table.add_row("mode", "demo" if profile.demo else "api")
    table.add_row("base_url", profile.base_url)
    table.add_row("username", profile.username or "-")
    table.add_row("org_id", profile.org_id or "-")
    table.add_row("config_dir", str(manager.config_dir))
    console.print(table)


@app.command()
def logout(
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to remove."),
) -> None:
    """Remove a saved profile and its token."""

    manager = ConfigManager()
    selected = profile
    if not selected:
        try:
            selected = manager.get_profile().name
        except ConfigurationError as exc:
            print_error(str(exc))
            raise typer.Exit(1) from exc
    assert selected is not None
    try:
        manager.delete_profile(selected)
    except ConfigurationError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    print_success(f"Profile '{selected}' removed.")
