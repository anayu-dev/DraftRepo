from __future__ import annotations

import typer

from copado_hx import __version__
from copado_hx.commands import auth, commit, deploy, promote, status, story
from copado_hx.demo import activate_demo_profile, show_demo_stories


app = typer.Typer(
    name="copado-hx",
    help="Terminal-first Copado DevOps lifecycle CLI for Salesforce developers.",
    no_args_is_help=True,
)

app.add_typer(auth.app, name="auth")
app.add_typer(story.app, name="story")
app.add_typer(commit.app, name="commit")
app.add_typer(promote.app, name="promote")
app.add_typer(deploy.app, name="deploy")
app.add_typer(status.app, name="status")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"copado-hx {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed version.",
    ),
) -> None:
    """Run Copado DevOps workflows without browser UI interaction."""


@app.command()
def demo(
    show_stories: bool = typer.Option(
        True,
        "--show-stories/--no-show-stories",
        help="Print sample user stories after activating demo mode.",
    ),
) -> None:
    """Activate demo mode backed by the mock Copado API."""

    activate_demo_profile()
    if show_stories:
        show_demo_stories()
