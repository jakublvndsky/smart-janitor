from rich.console import Console, ConsoleRenderable
from rich.panel import Panel
from rich.table import Table

from smart_janitor.models import ExecutionReport


def render_execution_report(report: ExecutionReport) -> list[ConsoleRenderable]:
    """Returns Rich objects"""
    parts: list[ConsoleRenderable] = []

    summary = Table.grid(padding=(0, 2))
    summary.add_row("[green]Successful[/green]", str(len(report.successful_moves)))
    summary.add_row("[red]Failed[/red]", str(len(report.failed_moves)))
    summary.add_row("[yellow]Skipped[/yellow]", str(len(report.skipped_moves)))
    if report.dry_run:
        summary.add_row("[dim]Mode[/dim]", "dry run")

    parts.append(Panel(summary, title="Summary", border_style="blue"))

    if report.successful_moves:
        t = Table(title="Successful moves", show_lines=True)
        t.add_column("Source", overflow="fold")
        t.add_column("Destination", overflow="fold")
        for move in report.successful_moves:
            t.add_row(str(move.src), str(move.dst))
        parts.append(t)

    if report.failed_moves:
        t = Table(title="Failed moves", show_lines=True)
        t.add_column("Source", overflow="fold")
        t.add_column("Destination", overflow="fold")
        t.add_column("Error Type", overflow="fold")
        t.add_column("Error Message", overflow="fold")
        for failed in report.failed_moves:
            t.add_row(
                str(failed.move.src),
                str(failed.move.dst),
                str(failed.error_type),
                failed.error_message,
            )
        parts.append(t)

    if report.skipped_moves:
        t = Table(title="Skipped moves", show_lines=True)
        t.add_column("Source", overflow="fold")
        t.add_column("Destination", overflow="fold")
        for skipped in report.skipped_moves:
            t.add_row(str(skipped.src), str(skipped.dst))
        parts.append(t)

    return parts


def print_execution_report(report: ExecutionReport, console: Console | None = None) -> None:
    console = console or Console()
    for part in render_execution_report(report):
        console.print(part)
