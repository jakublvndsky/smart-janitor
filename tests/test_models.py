from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from smart_janitor.models import (
    Age,
    Archive,
    ExecutionReport,
    Extension,
    FailedMove,
    Move,
    MoveTo,
    Rule,
    RunRecord,
)


def test_extension_normalizes_lowercase() -> None:
    ext = Extension(type="extension", pattern="PDF")
    assert ext.pattern == "pdf"


def test_extension_strips_leading_dot() -> None:
    ext = Extension(type="extension", pattern=".pdf")
    assert ext.pattern == "pdf"


def test_extension_handles_dot_and_uppercase() -> None:
    ext = Extension(type="extension", pattern=".PDF")
    assert ext.pattern == "pdf"


def test_age_rejects_negative_days() -> None:
    with pytest.raises(ValidationError):
        Age(type="age", older_than_days=-1)


def test_age_accepts_zero_days() -> None:
    age = Age(type="age", older_than_days=0)
    assert age.older_than_days == 0


def test_rule_discriminates_match_by_type() -> None:
    """Rule should parse the correct match subtype based on the 'type' field."""
    rule = Rule.model_validate(
        {
            "match": {"type": "extension", "pattern": "pdf"},
            "action": {"kind": "move_to", "dst": "/tmp"},
        }
    )
    assert isinstance(rule.match, Extension)


def test_rule_rejects_unknown_match_type() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(
            {
                "match": {"type": "unknown", "pattern": "x"},
                "action": {"kind": "move_to", "dst": "/tmp"},
            }
        )


def _exec_report() -> ExecutionReport:
    rule = Rule(
        match=Extension(type="extension", pattern="txt"),
        action=MoveTo(kind="move_to", dst=Path("/tmp/dst")),
    )
    move = Move(src=Path("/tmp/src/a.txt"), dst=Path("/tmp/dst/a.txt"), rule=rule)

    return ExecutionReport(
        successful_moves=[move, move],
        failed_moves=[
            FailedMove(
                move=move,
                error_type="source_missing",
                error_message="Missing",
            )
        ],
        dry_run=False,
    )


def test_execution_report_summary() -> None:
    report = _exec_report()

    assert report.summary == "Successful: 2 | Failed: 1 | Skipped: 0"


def test_execution_report_summary_true_dry_run(tmp_path: Path) -> None:
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    src = src_dir / "ghost.txt"
    src.write_text("new content")

    dst_dir = tmp_path / "dest"
    dst_dir.mkdir()
    existing = dst_dir / "ghost.txt"
    existing.write_text("original content")

    dst = dst_dir / "ghost.txt"
    exec_report = ExecutionReport(
        successful_moves=[
            Move(
                src=src,
                dst=dst,
                rule=Rule(
                    match=Extension(type="extension", pattern="txt"),
                    action=MoveTo(kind="move_to", dst=dst_dir),
                ),
            ),
            Move(
                src=src,
                dst=dst,
                rule=Rule(
                    match=Extension(type="extension", pattern="txt"),
                    action=MoveTo(kind="move_to", dst=dst_dir),
                ),
            ),
        ],
        failed_moves=[
            FailedMove(
                move=Move(
                    src=src,
                    dst=dst,
                    rule=Rule(
                        match=Extension(type="extension", pattern="txt"),
                        action=MoveTo(kind="move_to", dst=dst_dir),
                    ),
                ),
                error_type="destination_not_exists",
                error_message="Destination does not exits",
            ),
        ],
        skipped_moves=[
            Move(
                src=src,
                dst=dst,
                rule=Rule(
                    match=Extension(type="extension", pattern="txt"),
                    action=MoveTo(kind="move_to", dst=dst_dir),
                ),
            ),
        ],
        dry_run=True,
    )

    assert exec_report.summary == "Successful: 2 | Failed: 1 | Skipped: 1 | (dry run)"


def test_run_record_serialization_and_fields_check(tmp_path: Path) -> None:
    report = _exec_report()
    config = tmp_path / "rules.yaml"
    time = datetime.now(UTC)
    recorded_run = RunRecord(
        run_id=time.strftime("%Y%m%d-%H%M%S"),
        timestamp=time,
        scanned_path=Path("/tmp_path/src/"),
        config_path=config,
        report=report,
        undone=False,
    )
    serialized = recorded_run.model_dump_json(indent=2)
    model_reconstruction = recorded_run.model_validate_json(serialized)

    assert model_reconstruction.scanned_path == Path("/tmp_path/src/")
    assert model_reconstruction.timestamp.tzinfo is not None
    assert model_reconstruction.report.summary == "Successful: 2 | Failed: 1 | Skipped: 0"
    assert model_reconstruction.report.successful_moves == recorded_run.report.successful_moves
    assert (
        model_reconstruction.report.successful_moves[0].rule
        == recorded_run.report.successful_moves[0].rule
    )


def test_tilde_in_moveto() -> None:
    dst = Path("~/Documents/Archive")
    move = MoveTo(kind="move_to", dst=dst)
    assert move.dst == Path.home() / "Documents" / "Archive"


def test_tilde_in_archive() -> None:
    dst = Path("~/Archive")
    move = Archive(kind="archive", dst=dst)
    assert move.dst == Path.home() / "Archive"


def test_path_without_tilde() -> None:
    first_dst = MoveTo(kind="move_to", dst=Path("/tmp/dst"))
    second_dst = MoveTo(kind="move_to", dst=Path("sub/dir"))
    assert first_dst.dst == Path("/tmp/dst")
    assert second_dst.dst == Path("sub/dir")
