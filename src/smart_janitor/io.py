import shutil
from pathlib import Path
from typing import Literal

import yaml
from pydantic import ValidationError

from smart_janitor.models import (
    Config,
    ConfigError,
    ExecutionReport,
    FailedMove,
    FileInfo,
    Move,
    Rule,
)


def load_config(path: Path) -> list[Rule]:
    """Load and validate rules from YAML file"""
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")

    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML syntax in {path}: {e}") from e

    if data is None:
        return []

    try:
        config = Config.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f"Invalid config schema in {path}: {e}") from e

    return config.rules


def create_file_info(entry: Path) -> FileInfo:
    metadata = entry.stat()
    return FileInfo.model_validate(
        {
            "path": entry,
            "size": metadata.st_size,
            "mtime": metadata.st_mtime,
            "extension": entry.suffix,
        }
    )


def scan_directory(
    path: Path, recursive: bool = True, include_hidden: bool = False
) -> list[FileInfo]:
    """Scan directory and return FileInfo for each file"""
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    files = []
    iterator = path.rglob("*") if recursive else path.iterdir()
    for entry in iterator:
        if entry.name.startswith(".") and include_hidden is False:
            continue
        if entry.is_symlink():
            continue
        if not entry.is_file():
            continue
        files.append(create_file_info(entry))
    return files


def resolve_collision_name(dst_dir: Path, filename: str) -> Path:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = dst_dir / filename
    if not candidate.exists():
        return candidate

    i = 1
    while True:
        candidate = dst_dir / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _validate_preconditions(move: Move) -> FailedMove | None:
    """Check if move can be attempted. Return FailedMove if not, None if OK"""
    if not move.src.exists():
        return FailedMove(
            move=move,
            error_type="source_missing",
            error_message="Typed source is missing, please type correct one.",
        )
    return None


def _resolve_destination(
    move: Move, on_collision: Literal["skip", "rename", "overwrite"]
) -> Path | None:
    """Resolve final destination considering collisions. Return None to skip."""
    if not move.dst.exists():
        return move.dst

    match on_collision:
        case "skip":
            return None
        case "overwrite":
            return move.dst
        case "rename":
            return resolve_collision_name(move.dst.parent, move.dst.name)


def execute_moves(
    moves: list[Move],
    *,
    dry_run: bool = False,
    on_collision: Literal["skip", "rename", "overwrite"] = "skip",
) -> ExecutionReport:
    """Execute planned moves, returning a report of successes and failures"""
    successful: list[Move] = []
    failed: list[FailedMove] = []
    skipped: list[Move] = []

    for move in moves:
        error = _validate_preconditions(move)
        if error:
            failed.append(error)
            continue

        final_dst = _resolve_destination(move, on_collision)
        if final_dst is None:
            skipped.append(move)
            continue

        if not dry_run:
            final_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(move.src), str(final_dst))

        successful.append(move)

    return ExecutionReport(
        successful_moves=successful,
        failed_moves=failed,
        skipped_moves=skipped,
        dry_run=dry_run,
    )
