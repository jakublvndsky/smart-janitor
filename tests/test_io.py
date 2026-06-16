from datetime import UTC, datetime
from pathlib import Path

import pytest

from smart_janitor.io import execute_moves, load_config, scan_directory
from smart_janitor.models import ConfigError, Extension, Move, MoveTo, Rule

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_config_basic() -> None:
    rules = load_config(FIXTURES / "valid_basic.yaml")
    assert len(rules) == 4
    assert rules[0].match.type == "extension"


def test_load_config_minimal() -> None:
    rules = load_config(FIXTURES / "valid_minimal.yaml")
    assert len(rules) == 1


def test_load_config_empty_returns_empty_list() -> None:
    rules = load_config(FIXTURES / "valid_empty.yaml")
    assert rules == []


def test_load_config_raises_on_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/path.yaml"))


def test_load_config_raises_on_bad_yaml() -> None:
    with pytest.raises(ConfigError):  # zastąp swoim ConfigError
        load_config(FIXTURES / "invalid_yaml_syntax.yaml")


def test_load_config_raises_on_schema_violation() -> None:
    with pytest.raises(ConfigError):
        load_config(FIXTURES / "invalid_schema.yaml")


def test_load_config_raises_on_unknown_match_type() -> None:
    with pytest.raises(ConfigError):
        load_config(FIXTURES / "invalid_unknown_type.yaml")


## scan_drectory section


def test_scan_directory_empty_path(tmp_path: Path) -> None:
    (tmp_path / "empty_folder").mkdir()
    result = scan_directory(tmp_path)
    assert len(result) == 0


def test_scan_directory_checks_one_file(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a")
    result = scan_directory(tmp_path)
    assert len(result) == 1


@pytest.fixture
def flat_path(tmp_path: Path) -> Path:
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "test.pdf").write_text("test")
    (tmp_path / "test.csv").write_text("test")
    return tmp_path


def test_scan_directory_checks_multiple_files(flat_path: Path) -> None:
    result = scan_directory(flat_path)
    assert len(result) == 3


def test_scan_directory_checks_multiple_files_extensions(flat_path: Path) -> None:
    result = scan_directory(flat_path)
    extensions = {f.extension for f in result}
    assert extensions == {"txt", "pdf", "csv"}


@pytest.fixture
def two_level_path(tmp_path: Path) -> Path:
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("c")
    return tmp_path


def test_scan_directory_with_recursive_scanning(two_level_path: Path) -> None:
    result = scan_directory(two_level_path)
    assert len(result) == 3


def test_scan_directory_with_false_recursive_scanning(two_level_path: Path) -> None:
    result = scan_directory(two_level_path, recursive=False)
    assert len(result) == 2


def test_scan_directory_skips_symlink_to_file(tmp_path: Path) -> None:
    real = tmp_path / "real.txt"
    real.write_text("real")

    (tmp_path / "alias.txt").symlink_to(real)

    result = scan_directory(tmp_path)

    assert len(result) == 1
    assert result[0].path == real


def test_scan_directory_ignores_symlink_folder(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "sub" / "inside.txt").write_text("x")

    dir_link = tmp_path / "sub_link"
    dir_link.symlink_to(sub, target_is_directory=True)

    result = scan_directory(tmp_path)
    paths = {f.path for f in result}

    assert len(result) == 1
    assert tmp_path / "sub_link" not in paths


@pytest.mark.parametrize(
    "hidden_name",
    [".DS_Store", ".gitignore", ".env", ".hidden_dir"],
)
def test_hidden_entries_ignored(tmp_path: Path, hidden_name: str) -> None:
    (tmp_path / "real.txt").write_text("x")
    if hidden_name.endswith("_dir"):
        (tmp_path / hidden_name).mkdir()
    else:
        (tmp_path / hidden_name).write_text("x")

    result = scan_directory(tmp_path)

    names = {f.path.name for f in result}
    assert hidden_name not in names
    assert "real.txt" in names


def test_scan_directory_raises_path_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        scan_directory(tmp_path / "nonexistent")


def test_scan_directory_raises_not_a_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("This is a file, not a folder")

    with pytest.raises(NotADirectoryError):
        scan_directory(file_path)


@pytest.fixture
def metadata_correctness_path(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("hello")
    return tmp_path


def test_scan_directory_check_metadata_correct_size(metadata_correctness_path: Path) -> None:
    result = scan_directory(metadata_correctness_path)
    assert result[0].size == 5


def test_scan_directory_check_metadata_correct_mtime(metadata_correctness_path: Path) -> None:
    result = scan_directory(metadata_correctness_path)
    now = datetime.now(UTC)

    mtime = result[0].mtime

    assert abs((mtime - now).total_seconds()) < 5


def test_scan_directory_check_metadata_extension_noramlization(tmp_path: Path) -> None:
    (tmp_path / "Photo.JPG").write_text("Photo")
    (tmp_path / "report.PDF").write_text("report")

    result = scan_directory(tmp_path)

    assert {"jpg", "pdf"} == {f.extension for f in result}


## execute moves
def test_execute_moves_relocates_file(tmp_path: Path) -> None:
    # Arrange
    src = tmp_path / "source.txt"
    src.write_text("important content")
    dst_file = tmp_path / "destination" / "source.txt"

    move = Move(
        src=src,
        dst=dst_file,
        rule=Rule(
            match=Extension(type="extension", pattern="txt"),
            action=MoveTo(kind="move_to", dst=tmp_path / "destination"),
        ),
    )

    report = execute_moves([move])

    assert len(report.successful_moves) == 1
    assert len(report.failed_moves) == 0

    assert dst_file.exists()
    assert dst_file.read_text() == "important content"

    assert not src.exists()


def test_execute_moves_dry_run_does_not_touch_filesystem(tmp_path: Path) -> None:
    src = tmp_path / "source.txt"
    src.write_text("important")
    dst = tmp_path / "dest" / "source.txt"
    move = Move(
        src=src,
        dst=dst,
        rule=Rule(
            match=Extension(type="extension", pattern=".txt"),
            action=MoveTo(kind="move_to", dst=dst),
        ),
    )

    # Act
    report = execute_moves([move], dry_run=True)

    assert len(report.successful_moves) == 1
    assert report.dry_run is True

    assert src.exists()
    assert not dst.exists()


def test_execute_moves_missing_source_goes_to_failed(tmp_path: Path) -> None:
    dst = tmp_path / "dest" / "ghost.txt"
    move = Move(
        src=tmp_path / "ghost.txt",
        dst=dst,
        rule=Rule(
            match=Extension(type="extension", pattern="txt"),
            action=MoveTo(kind="move_to", dst=tmp_path / "dest"),
        ),
    )

    report = execute_moves([move])

    assert len(report.failed_moves) == 1
    assert report.failed_moves[0].error_type == "source_missing"
    assert len(report.successful_moves) == 0
    assert not dst.exists()


def test_execute_moves_on_collision_goes_to_skipped(tmp_path: Path) -> None:
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    src = src_dir / "ghost.txt"
    src.write_text("new content")

    dst_dir = tmp_path / "dest"
    dst_dir.mkdir()
    existing = dst_dir / "ghost.txt"
    existing.write_text("original content")

    dst = dst_dir / "ghost.txt"
    move = Move(
        src=src,
        dst=dst,
        rule=Rule(
            match=Extension(type="extension", pattern="txt"),
            action=MoveTo(kind="move_to", dst=dst_dir),
        ),
    )

    report = execute_moves([move])

    assert len(report.skipped_moves) == 1
    assert len(report.successful_moves) == 0
    assert src.exists()
    assert dst.read_text() == "original content"


def test_execute_moves_on_collision_overwrite_goes_to_successful(tmp_path: Path) -> None:
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    src = src_dir / "ghost.txt"
    src.write_text("new content")

    dst_dir = tmp_path / "dest"
    dst_dir.mkdir()
    existing = dst_dir / "ghost.txt"
    existing.write_text("original content")

    dst = dst_dir / "ghost.txt"
    move = Move(
        src=src,
        dst=dst,
        rule=Rule(
            match=Extension(type="extension", pattern="txt"),
            action=MoveTo(kind="move_to", dst=dst_dir),
        ),
    )

    report = execute_moves([move], on_collision="overwrite")

    assert len(report.successful_moves) == 1
    assert len(report.skipped_moves) == 0
    assert not src.exists()
    assert dst.read_text() == "new content"


def test_execute_moves_on_collision_rename_goes_to_successful(tmp_path: Path) -> None:
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    src = src_dir / "ghost.txt"
    src.write_text("new content")

    dst_dir = tmp_path / "dest"
    dst_dir.mkdir()
    existing = dst_dir / "ghost.txt"
    existing.write_text("original content")

    dst = dst_dir / "ghost.txt"
    move = Move(
        src=src,
        dst=dst,
        rule=Rule(
            match=Extension(type="extension", pattern="txt"),
            action=MoveTo(kind="move_to", dst=dst_dir),
        ),
    )

    report = execute_moves([move], on_collision="rename")

    assert len(report.successful_moves) == 1
    assert len(report.skipped_moves) == 0
    assert not src.exists()
    assert (dst_dir / "ghost_1.txt").exists()
    assert dst.read_text() == "original content"


def test_execute_moves_on_collision_check_and_rename_second_file_which_goes_to_successful(
    tmp_path: Path,
) -> None:
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    src = src_dir / "ghost.txt"
    src.write_text("new content")

    dst_dir = tmp_path / "dest"
    dst_dir.mkdir()
    existing = dst_dir / "ghost.txt"
    existing.write_text("original content")

    existing_sec = dst_dir / "ghost_1.txt"
    existing_sec.write_text("original content")

    dst = dst_dir / "ghost.txt"
    move = Move(
        src=src,
        dst=dst,
        rule=Rule(
            match=Extension(type="extension", pattern="txt"),
            action=MoveTo(kind="move_to", dst=dst_dir),
        ),
    )

    report = execute_moves([move], on_collision="rename")

    assert len(report.successful_moves) == 1
    assert len(report.skipped_moves) == 0
    assert not src.exists()
    assert (dst_dir / "ghost_2.txt").exists()
    assert dst.read_text() == "original content"
