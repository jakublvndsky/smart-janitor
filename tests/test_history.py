from datetime import UTC, datetime
from pathlib import Path

from smart_janitor.history import save_run
from smart_janitor.models import (
    ExecutionReport,
    Extension,
    FailedMove,
    Move,
    MoveTo,
    Rule,
    RunRecord,
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


def _run_record_(tmp_path: Path) -> RunRecord:
    report = _exec_report()
    config = tmp_path / "rules.yaml"
    time = datetime.now(UTC)
    return RunRecord(
        run_id=time.strftime("%Y%m%d-%H%M%S"),
        timestamp=time,
        scanned_path=Path("/tmp_path/src/"),
        config_path=config,
        report=report,
        undone=False,
    )


def test_save_run_correct_path(tmp_path: Path) -> None:
    history_dir = tmp_path / "smart-janitor" / "history"
    record = _run_record_(tmp_path)

    file_name = record.run_id + ".json"
    full_path = history_dir / file_name

    saved_run = save_run(record=record, history_dir=history_dir)

    with open(full_path) as f:
        file_content = f.read()

    assert saved_run == full_path
    assert record.model_validate_json(file_content)
