from __future__ import annotations

import json
from typing import Iterable

from rich.console import Console
from rich.table import Table

from copado_hx.lib.api import OperationResult, UserStory


console = Console()


def print_json(value: object) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    elif isinstance(value, Iterable) and not isinstance(value, (dict, str, bytes)):
        value = [item.model_dump() if hasattr(item, "model_dump") else item for item in value]
    console.print_json(json.dumps(value, default=str))


def print_story_table(stories: list[UserStory]) -> None:
    table = Table(title="Copado User Stories")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Status", style="green")
    table.add_column("Source")
    table.add_column("Target")
    table.add_column("Release")
    for story in stories:
        table.add_row(
            story.key,
            story.name,
            story.status,
            story.source_org or "-",
            story.target_org or "-",
            story.release or "-",
        )
    console.print(table)


def print_story(story: UserStory) -> None:
    table = Table(title=f"User Story {story.key}")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    values = story.model_dump()
    for key in sorted(values):
        table.add_row(key, str(values[key] if values[key] is not None else "-"))
    console.print(table)


def print_operation(result: OperationResult) -> None:
    table = Table(title="Copado Operation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("id", result.id)
    table.add_row("status", result.status)
    table.add_row("message", result.message or "-")
    for key, value in sorted(result.data.items()):
        table.add_row(key, str(value))
    console.print(table)


def print_operations(results: list[OperationResult]) -> None:
    table = Table(title="Copado Pipeline Status")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Message")
    table.add_column("Story")
    for result in results:
        table.add_row(
            result.id,
            result.status,
            result.message or "-",
            str(result.data.get("story_id", "-")),
        )
    console.print(table)


def print_success(message: str) -> None:
    console.print(f"[bold green]OK[/bold green] {message}")


def print_warning(message: str) -> None:
    console.print(f"[bold yellow]WARN[/bold yellow] {message}")


def print_error(message: str) -> None:
    console.print(f"[bold red]ERROR[/bold red] {message}")
