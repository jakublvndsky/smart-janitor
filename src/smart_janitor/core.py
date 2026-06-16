import re
from datetime import UTC, datetime
from typing import assert_never

from smart_janitor.models import (
    Age,
    Archive,
    Extension,
    FileInfo,
    Move,
    MoveTo,
    Regex,
    Rename,
    Rule,
    Size,
)


def _match_extension(file_extension: str, rule_extension: str) -> bool:
    """Check if file's extension matches the rule's extension."""
    return file_extension == rule_extension


def _match_size(file_size: int, rule_file_size: float, unit: str, operator: str) -> bool:
    """Check if file's size matches the rule's size."""
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    rule_size = rule_file_size * multipliers[unit]
    return (
        (operator == "lt" and file_size < rule_size)
        or (operator == "eq" and file_size == rule_size)
        or (operator == "gt" and file_size > rule_size)
    )


def _match_regex(pattern: str, filename: str) -> bool:
    """Check if file's name matches the rule's regex pattern."""
    return re.search(pattern, filename) is not None


def _match_days(file_mtime: datetime, rule_days: int) -> bool:
    """Check if file's modified time is greater then the rule's older_than_days."""
    now = datetime.now(UTC)
    file_age = now - file_mtime.astimezone(UTC)
    return file_age.days > rule_days


def match_rule(file: FileInfo, rule: Rule) -> bool:
    match rule.match:
        case Extension(pattern=ext):
            return _match_extension(file.extension, ext)
        case Size(threshold=t, unit=u, operator=o):
            return _match_size(file.size, t, u, o)
        case Regex(pattern=pattern):
            return _match_regex(pattern, file.path.name)
        case Age(older_than_days=days):
            return _match_days(file.mtime, days)
        case _ as unreachable:
            assert_never(unreachable)


def plan_moves(files: list[FileInfo], rules: list[Rule]) -> list[Move]:
    moves: list[Move] = []
    for file in files:
        for rule in rules:
            if not match_rule(file, rule):
                continue
            match rule.action:
                case MoveTo(dst=d) | Archive(dst=d):
                    moves.append(Move(src=file.path, dst=d, rule=rule))
                    break
                case Rename():
                    # TODO - implement later, requires rename-in-place vs move semantics
                    break
    return moves
