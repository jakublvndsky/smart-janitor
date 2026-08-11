from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from smart_janitor.history import list_runs, load_run, mark_run_as_undone, save_run
from smart_janitor.models import (
    ExecutionReport,
    Extension,
    FailedMove,
    Move,
    MoveTo,
    Rule,
    RunNotFoundError,
    RunRecord,
)

FIXTURES = Path(__file__).parent / "fixtures" / "history"


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


def test_save_run_file_already_exists(tmp_path: Path) -> None:
    history_dir = tmp_path / "smart-janitor" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    record = _run_record_(tmp_path)

    file_name = record.run_id + ".json"
    file_exists = history_dir / file_name
    file_exists.write_text("Already exists")

    with pytest.raises(FileExistsError):
        save_run(record=record, history_dir=history_dir)


def test_list_runs_sorted_files() -> None:
    records = list_runs(FIXTURES)
    assert len(records) == 3
    assert records[0].run_id == "20240701-090000"


def test_list_runs_skip_invalid_files() -> None:
    records = list_runs(FIXTURES)
    ids = {r.run_id for r in records}
    assert "broken" not in ids


def test_load_run_correct_record() -> None:
    run_id = "20240701-090000"
    record = load_run(run_id=run_id, history_dir=FIXTURES)
    assert record.run_id == "20240701-090000"


def test_load_run_validation_error() -> None:
    with pytest.raises(ValidationError):
        load_run(run_id="invalid", history_dir=FIXTURES)


def test_load_run_raises_when_run_id_not_found(tmp_path: Path) -> None:
    missing_dir = tmp_path / "test_directory"
    missing_dir.mkdir(parents=True)
    with pytest.raises(RunNotFoundError):
        load_run(run_id="99999999-999999", history_dir=missing_dir)


def test_list_runs_on_empty_folder(tmp_path: Path) -> None:
    empty_dir = tmp_path / "history" / "runs"
    empty_dir.mkdir(parents=True)
    response = list_runs(empty_dir)
    assert response == []


def test_round_trip(tmp_path: Path) -> None:
    history_dir = tmp_path / "smart-janitor" / "history"
    record = _run_record_(tmp_path)
    history_dir.mkdir(parents=True)

    saved_run = save_run(record=record, history_dir=history_dir)
    loaded_run = load_run(run_id=record.run_id, history_dir=history_dir)

    loaded_dir = history_dir / (loaded_run.run_id + ".json")

    assert record.run_id == loaded_run.run_id
    assert saved_run == loaded_dir
    assert record == loaded_run


def test_mark_run_as_undone(tmp_path: Path) -> None:
    history_dir = tmp_path / "smart-janitor" / "history"
    record = _run_record_(tmp_path)
    history_dir.mkdir(parents=True)

    save_run(record=record, history_dir=history_dir)
    marked_run = mark_run_as_undone(run_id=record.run_id, history_dir=history_dir)

    reloaded = load_run(run_id=record.run_id, history_dir=history_dir)

    assert marked_run.undone is True
    assert record.undone is False and marked_run.undone is True
    assert reloaded.undone is True
