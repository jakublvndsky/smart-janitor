from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from smart_janitor.core import plan_moves
from smart_janitor.io import execute_moves, load_config, scan_directory
from smart_janitor.models import ConfigError, Move
from smart_janitor.reporting import print_execution_report


class CollisionStrategy(StrEnum):
    skip = "skip"
    rename = "rename"
    overwrite = "overwrite"


def print_moves(moves: list[Move]) -> None:
    if not moves:
        Console().print("[dim]Nothing to do — no files matched the rules.[/dim]")
        return
    console = Console()
    table = Table(title="Planned Moves")
    table.add_column("Source", style="cyan", overflow="fold")
    table.add_column("Destination", style="green", overflow="fold")
    table.add_column("Rule", style="dim")

    for move in moves:
        match = move.rule.match
        match_desc = f"{match.type}: {getattr(match, 'pattern', getattr(match, 'threshold', ''))}"
        table.add_row(str(move.src), str(move.dst), match_desc)

    console.print(table)
    console.print(f"[bold]{len(moves)}[/bold] files to move")


SAMPLE_CONFIG = """# Smart Janitor — rules configuration
# Documentation: https://github.com/jakublvndsky/smart-janitor

version: 1
rules:
  # Move PDFs older than 30 days to archive
  - match:
      type: age
      older_than_days: 30
    action:
      kind: archive
      dst: ~/Documents/Archive

  # Move images to Pictures folder
  - match:
      type: extension
      pattern: jpg
    action:
      kind: move_to
      dst: ~/Pictures

  # Move large files (>500MB) to external drive
  - match:
      type: size
      threshold: 500
      unit: MB
      operator: gt
    action:
      kind: move_to
      dst: /Volumes/External/LargeFiles

  # Move screenshots to dedicated folder
  - match:
      type: regex
      pattern: "^Screenshot.*\\.png$"
    action:
      kind: move_to
      dst: ~/Pictures/Screenshots """

app = typer.Typer(help="Tidy up messy folders based on declarative YAML rules.")


@app.command()
def init(
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Where to write rules.yaml")
    ] = Path("rules.yaml"),
) -> None:
    """Generate a sample rules.yaml in the current directory."""
    if output.is_file():
        typer.echo(f"File with this name already exists: {output.name}")
        raise typer.Exit(1)
    else:
        output.write_text(SAMPLE_CONFIG)
        typer.echo(f"Created sample config at {output}")


@app.command()
def plan(
    path: Annotated[Path, typer.Argument(help="Directory to scan")],
    config: Annotated[Path, typer.Option("--config", "-c", help="Path to rules.yaml")] = Path(
        "rules.yaml"
    ),
    recursive: bool = True,
    include_hidden: bool = False,
) -> None:
    """Preview what would be moved, without changing anything."""
    try:
        config_rules = load_config(config)
        scanned_files = scan_directory(
            path=path, recursive=recursive, include_hidden=include_hidden
        )
    except (ConfigError, FileNotFoundError, NotADirectoryError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    planned_moves = plan_moves(files=scanned_files, rules=config_rules)
    print_moves(planned_moves)


@app.command()
def run(
    path: Annotated[Path, typer.Argument(help="Directory to scan")],
    config: Annotated[Path, typer.Option("--config", "-c", help="Path to rules.yaml")] = Path(
        "rules.yaml"
    ),
    recursive: bool = True,
    include_hidden: bool = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-dr", help="Execute dry run")] = False,
    on_collision: Annotated[
        CollisionStrategy,
        typer.Option("--on-collision", "-oc", help="How should execution behave on collision"),
    ] = CollisionStrategy.skip,
) -> None:
    """Execute the tidying: scan, plan, and move files."""
    try:
        config_rules = load_config(config)
        scanned_files = scan_directory(
            path=path, recursive=recursive, include_hidden=include_hidden
        )
    except (ConfigError, FileNotFoundError, NotADirectoryError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    planned_moves = plan_moves(files=scanned_files, rules=config_rules)
    exec_report = execute_moves(
        moves=planned_moves, dry_run=dry_run, on_collision=on_collision.value
    )

    print_execution_report(exec_report)


if __name__ == "__main__":
    app()
