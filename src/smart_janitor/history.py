from pathlib import Path

from smart_janitor.models import RunRecord

BASE_DIR = Path(__file__).resolve().parent


_full_dir_path = BASE_DIR / "smart-janitor" / "history"


def save_run(record: RunRecord, history_dir: Path = _full_dir_path) -> Path:
    # Saves JSON and returns the path
    if not history_dir.exists():
        print(f"Directory Not Found: {history_dir}")
        print(" --- Creating Directory --- ")
        history_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created Directory: {history_dir}")

    file_name = record.run_id + ".json"
    full_path = history_dir / file_name
    if full_path.exists():
        raise FileExistsError(f"File with this name already exists: {full_path.name}")

    file_content = record.model_dump_json(indent=2)
    with open(full_path, "w") as f:
        f.write(file_content)
    print(f"File created here: {full_path}")
    return full_path


def list_runs(history_dir: Path) -> str:  # list[RunRecord]:
    # Reads all the logs and sort them by date
    return "pass"


def load_run(run_id: str, history_dir: Path) -> str:  # RunRecord:
    # Loads exact run
    return "pass"
