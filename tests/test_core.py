from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from smart_janitor.core import (
    _match_days,
    _match_extension,
    _match_regex,
    _match_size,
    match_rule,
    plan_moves,
)
from smart_janitor.models import Age, Archive, Extension, FileInfo, MoveTo, Regex, Rule, Size


@pytest.mark.parametrize(
    "file_ext,rule_ext,expected",
    [
        ("pdf", "pdf", True),
        ("pdf", "jpg", False),
        ("jpg", "jpg", True),
        ("jpg", "pdf", False),
        ("", "", True),
    ],
)
def test_match_extension(file_ext: str, rule_ext: str, expected: bool) -> None:
    assert _match_extension(file_ext, rule_ext) is expected


@pytest.mark.parametrize(
    "file_size,rule_file_size,unit,operator,expected",
    [
        # less than - plik mniejszy niż próg
        (80, 8, "MB", "lt", True),
        (10, 8, "B", "lt", False),
        # greater than - plik większy niż próg
        (8 * 1024 * 1024 + 1, 8, "MB", "gt", True),
        (10, 11, "B", "gt", False),
        # equal
        (10, 10, "B", "eq", True),
        (11, 8, "B", "eq", False),
    ],
)
def test_match_size(
    file_size: int, rule_file_size: float, unit: str, operator: str, expected: bool
) -> None:
    assert _match_size(file_size, rule_file_size, unit, operator) is expected


@pytest.mark.parametrize(
    "pattern,filename,expected",
    [
        # Exact date in file name
        (r"\d{4}-\d{2}-\d{2}", "raport_2024-05-29.csv", True),
        (r"\d{4}-\d{2}-\d{2}", "raport_maj2024.csv", False),
        # File extension
        (r"\.(jpg|png|gif|pdf)$", "photo_2024.pdf", True),
        (r"\.(jpg|png)$", "banner.gif", False),
        # Absolute path
        (r"^(/[\w\-\.]+)+", "/home/user/documents/file.txt", True),
        (r"^(/[\w\-\.]+)+", "home/user/file.txt", False),
    ],
)
def test_match_regex(pattern: str, filename: str, expected: bool) -> None:
    assert _match_regex(pattern, filename) is expected


@pytest.mark.parametrize(
    "days_old,rule_days,expected",
    [(60, 30, True), (10, 30, False), (30, 30, False), (31, 30, True)],
)
def test_match_days(days_old: int, rule_days: int, expected: bool) -> None:
    file_mtime = datetime.now(UTC) - timedelta(days=days_old)
    assert _match_days(file_mtime, rule_days) is expected


@pytest.fixture
def jpg_file() -> FileInfo:
    return FileInfo(
        path=Path("/tmp/test.jpg"),
        size=300,
        mtime=datetime(2024, 1, 1, tzinfo=UTC),
        extension="jpg",
    )


@pytest.fixture
def pdf_file() -> FileInfo:
    return FileInfo(
        path=Path("/tmp/test.pdf"),
        size=500,
        mtime=datetime(2025, 1, 1, tzinfo=UTC),
        extension="pdf",
    )


def test_match_rule_dispatches_to_extension_match(jpg_file: FileInfo) -> None:
    rule = Rule(
        match=Extension(type="extension", pattern="jpg"),
        action=MoveTo(kind="move_to", dst=Path("./src/tests/")),
    )
    assert match_rule(jpg_file, rule)


def test_match_rule_returns_false_when_extension_differs(jpg_file: FileInfo) -> None:
    rule = Rule(
        match=Extension(type="extension", pattern="pdf"),
        action=MoveTo(kind="move_to", dst=Path("/tmp/dst")),
    )
    assert match_rule(jpg_file, rule) is False


def test_match_rule_size_match(jpg_file: FileInfo) -> None:
    rule = Rule(
        match=Size(type="size", threshold=50, unit="B", operator="gt"),
        action=MoveTo(kind="move_to", dst=Path("./src/tests/")),
    )
    assert match_rule(jpg_file, rule)


def test_match_rule_returns_false_when_size_operator_is_not_correct(jpg_file: FileInfo) -> None:
    rule = Rule(
        match=Size(type="size", threshold=50, unit="MB", operator="gt"),
        action=MoveTo(kind="move_to", dst=Path("./src/tests/")),
    )
    assert match_rule(jpg_file, rule) is False


def test_match_rule_when_regex_search_is_true(jpg_file: FileInfo) -> None:
    rule = Rule(
        match=Regex(type="regex", pattern=r"\.(jpg|png|gif|pdf)$"),
        action=Archive(kind="archive", dst=Path("/tmp/test.jpg")),
    )
    assert match_rule(jpg_file, rule)


def test_match_rule_age_older_than_rule_days(jpg_file: FileInfo) -> None:
    rule = Rule(
        match=Age(type="age", older_than_days=50),
        action=Archive(kind="archive", dst=Path("/tmp/test.jpg")),
    )
    assert match_rule(jpg_file, rule)


def test_plan_moves(jpg_file: FileInfo, pdf_file: FileInfo) -> None:
    files = [jpg_file, pdf_file]
    rule_1 = Rule(
        match=Extension(type="extension", pattern="pdf"),
        action=MoveTo(kind="move_to", dst=Path("/tmp/dst")),
    )
    rule_2 = Rule(
        match=Regex(type="regex", pattern=r"\.(jpg|png|gif|pdf)$"),
        action=Archive(kind="archive", dst=Path("/tmp/test.jpg")),
    )
    rules = [rule_1, rule_2]
    moves = plan_moves(files, rules)

    assert len(moves) == 2

    jpg_move = next(m for m in moves if m.src == jpg_file.path)
    assert jpg_move.dst == Path("/tmp/test.jpg")

    pdf_move = next(m for m in moves if m.src == pdf_file.path)
    assert pdf_move.dst == Path("/tmp/dst")


def test_match_rule_normalizes_extensions() -> None:
    """Verify that uppercase extensions match through model normalization."""
    file = FileInfo(
        path=Path("/tmp/test.PDF"),
        size=100,
        mtime=datetime(2024, 1, 1, tzinfo=UTC),
        extension=".PDF",
    )
    rule = Rule(
        match=Extension(type="extension", pattern="PDF"),
        action=MoveTo(kind="move_to", dst=Path("/tmp")),
    )
    assert match_rule(file, rule) is True


def test_match_size_raises_on_invalid_unit() -> None:
    with pytest.raises(KeyError):
        _match_size(100, 1.0, "TB", "lt")


def test_plan_moves_first_matching_rule_wins(jpg_file: FileInfo) -> None:
    """When file matches multiple rules, only first one is applied."""
    rule_first = Rule(
        match=Extension(type="extension", pattern="jpg"),
        action=MoveTo(kind="move_to", dst=Path("/tmp/first")),
    )
    rule_second = Rule(
        match=Extension(type="extension", pattern="jpg"),
        action=MoveTo(kind="move_to", dst=Path("/tmp/second")),
    )
    moves = plan_moves([jpg_file], [rule_first, rule_second])

    assert len(moves) == 1
    assert moves[0].dst == Path("/tmp/first")
