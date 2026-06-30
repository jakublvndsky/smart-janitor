# tests/test_reporting.py
from pathlib import Path

from smart_janitor.models import ExecutionReport, Extension, FailedMove, Move, MoveTo, Rule
from smart_janitor.reporting import render_execution_report


def _make_move() -> Move:
    return Move(
        src=Path("/tmp/src/a.txt"),
        dst=Path("/tmp/dst/a.txt"),
        rule=Rule(
            match=Extension(type="extension", pattern="txt"),
            action=MoveTo(kind="move_to", dst=Path("/tmp/dst")),
        ),
    )


def test_render_includes_failed_section() -> None:
    move = _make_move()
    report = ExecutionReport(
        failed_moves=[FailedMove(move=move, error_type="source_missing", error_message="gone")],
        dry_run=False,
    )
    parts = render_execution_report(report)
    # Summary panel + failed table = 2 elementy
    assert len(parts) == 2


def test_render_includes_skipped_section() -> None:
    move = _make_move()
    report = ExecutionReport(skipped_moves=[move], dry_run=False)
    parts = render_execution_report(report)
    assert len(parts) == 2


def test_render_only_summary_when_empty() -> None:
    report = ExecutionReport(dry_run=False)
    parts = render_execution_report(report)
    assert len(parts) == 1  # tylko summary panel
