import logging
from pathlib import Path

from pydantic import ValidationError

from smart_janitor.models import RunNotFoundError, RunRecord


def save_run(record: RunRecord, history_dir: Path) -> Path:
    """Saves JSON and returns the path"""
    history_dir.mkdir(parents=True, exist_ok=True)

    file_name = record.run_id + ".json"
    full_path = history_dir / file_name
    if full_path.exists():
        raise FileExistsError(f"File with this name already exists: {full_path.name}")

    file_content = record.model_dump_json(indent=2)
    with open(full_path, "w") as f:
        f.write(file_content)

    return full_path


def list_runs(history_dir: Path) -> list[RunRecord]:
    """Reads all the logs and sort them by date"""

    run_records: list[RunRecord] = []
    for path in history_dir.glob("*.json"):
        with open(path) as f:
            file_content = f.read()
            try:
                record = RunRecord.model_validate_json(file_content)
                run_records.append(record)
            except ValidationError:
                logging.warning(f"There is a problem to validate this file: {path.name}")
                continue

    if not run_records:
        return []

    sorted_runs = sorted(run_records, key=lambda record: record.run_id, reverse=True)
    return sorted_runs


def load_run(run_id: str, history_dir: Path) -> RunRecord:
    """Loads exact run"""
    if not history_dir.exists():
        raise FileNotFoundError(f"Could not find a directory: {history_dir}")

    for path in history_dir.glob("*.json"):
        if run_id == path.stem:
            with open(path) as f:
                file_content = f.read()
                record = RunRecord.model_validate_json(file_content)
                return record

    raise RunNotFoundError(f"Run {run_id} not found in {history_dir}")


def mark_run_as_undone(run_id: str, history_dir: Path) -> RunRecord:
    file_path = history_dir / (run_id + ".json")
    record = load_run(run_id=run_id, history_dir=history_dir)
    copied_model = record.model_copy(update={"undone": True})

    file_content = copied_model.model_dump_json(indent=2)

    with open(file_path, "w") as f:
        f.write(file_content)

    return copied_model
