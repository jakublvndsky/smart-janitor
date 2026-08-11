from pathlib import Path

import pytest
from typer.testing import CliRunner

from smart_janitor.cli import app
from smart_janitor.history import list_runs
from smart_janitor.io import load_config

runner = CliRunner()


@pytest.fixture
def cli_setup(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Returns (scan_dir, config_path)."""
    scan_dir = tmp_path / "messy"
    scan_dir.mkdir()
    (scan_dir / "photo.jpg").write_text("x")

    dest_dir = tmp_path / "sorted"

    config = tmp_path / "rules.yaml"
    config.write_text(
        f"""
version: 1
rules:
  - match:
      type: extension
      pattern: jpg
    action:
      kind: move_to
      dst: {tmp_path / "sorted"}
"""
    )
    return scan_dir, config, dest_dir


def test_init_creates_config(tmp_path: Path) -> None:
    output = tmp_path / "rules.yaml"
    result = runner.invoke(app, ["init", "--output", str(output)])
    assert result.exit_code == 0
    assert output.exists()
    assert "rules:" in output.read_text()


def test_init_refuses_to_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "rules.yaml"
    output.write_text("existing")
    result = runner.invoke(app, ["init", "--output", str(output)])
    assert result.exit_code == 1
    assert output.read_text() == "existing"


def test_plan_with_correct_config(cli_setup: tuple[Path, Path, Path]) -> None:
    scan_dir, config, _dest_dir = cli_setup
    result = runner.invoke(app, ["plan", str(scan_dir), "--config", str(config)])
    assert result.exit_code == 0
    assert "photo.jpg" in result.output
    assert "Planned Moves" in result.output
    assert "sorted" in result.output


def test_plan_with_wrong_config(cli_setup: tuple[Path, Path, Path], tmp_path: Path) -> None:
    scan_dir = cli_setup[0]

    bad_config = tmp_path / "bad_config.yaml"
    bad_config.write_text("""
    version: 1
    rules:
      - match:
            type: owner
            pattern: kuba
        action:
            kind: move_to
            dst: /tmp/test
    """)
    result = runner.invoke(app, ["plan", str(scan_dir), "--config", str(bad_config)])
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_run_moving_files(cli_setup: tuple[Path, Path, Path]) -> None:
    scan_dir, config, dest_dir = cli_setup
    result = runner.invoke(app, ["run", str(scan_dir), "--config", str(config), "--yes"])
    assert result.exit_code == 0
    assert not (scan_dir / "photo.jpg").exists()
    assert (dest_dir / "photo.jpg").exists()


def test_run_dry_run_without_moving_files(cli_setup: tuple[Path, Path, Path]) -> None:
    scan_dir, config, dest_dir = cli_setup
    result = runner.invoke(app, ["run", str(scan_dir), "--config", str(config), "--dry-run"])
    assert result.exit_code == 0
    assert (scan_dir / "photo.jpg").exists()
    assert not (dest_dir / "photo.jpg").exists()


def test_run_config_errors(tmp_path: Path) -> None:
    scan_dir = tmp_path / "scanned"
    config = tmp_path / "invalid.json"

    result = runner.invoke(app, ["run", str(scan_dir), "--config", str(config), "--yes"])

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_history_after_run_moving_files(cli_setup: tuple[Path, Path, Path], tmp_path: Path) -> None:
    scan_dir, config, dest_dir = cli_setup
    history_dir = tmp_path / "smart-janitor" / "history"
    history_dir.mkdir(parents=True)
    result = runner.invoke(
        app, ["run", str(scan_dir), "--config", str(config), "--history-dir", str(history_dir), "--yes"]
    )

    history_runs = list_runs(history_dir=history_dir)
    history = runner.invoke(
        app, ["history", "--history-dir", str(history_dir)], env={"COLUMNS": "200"}
    )

    assert result.exit_code == 0
    assert history.exit_code == 0
    assert len(history_runs) == 1
    assert "Run history" in history.output
    assert f"{history_runs[0].run_id[:8]}" in history.output
    assert (dest_dir / "photo.jpg").exists()


def test_undo_after_run_moving_files(cli_setup: tuple[Path, Path, Path], tmp_path: Path) -> None:
    scan_dir, config, dest_dir = cli_setup
    history_dir = tmp_path / "smart-janitor" / "history"
    history_dir.mkdir(parents=True)
    result = runner.invoke(
        app, ["run", str(scan_dir), "--config", str(config), "--history-dir", str(history_dir), "--yes"]
    )

    history_runs = list_runs(history_dir=history_dir)
    undo_result = runner.invoke(
        app, ["undo", str(history_runs[0].run_id), "--history-dir", str(history_dir), "--yes"]
    )

    assert result.exit_code == 0
    assert undo_result.exit_code == 0
    assert (scan_dir / "photo.jpg").exists()
    assert not (dest_dir / "photo.jpg").exists()


def test_undo_with_invalid_run_id() -> None:
    result = runner.invoke(
        app,
        [
            "undo",
            "invalid",
        ],
    )
    assert result.exit_code == 1
    assert "Error: " in result.output


def test_undo_two_times_on_the_same_run(cli_setup: tuple[Path, Path, Path], tmp_path: Path) -> None:
    scan_dir, config, _ = cli_setup
    history_dir = tmp_path / "smart-janitor" / "history"
    history_dir.mkdir(parents=True)
    result = runner.invoke(
        app, ["run", str(scan_dir), "--config", str(config), "--history-dir", str(history_dir), "--yes"]
    )

    history_runs = list_runs(history_dir=history_dir)
    undo_result = runner.invoke(
        app, ["undo", str(history_runs[0].run_id), "--history-dir", str(history_dir), "--yes"]
    )

    second_undo = runner.invoke(
        app, ["undo", str(history_runs[0].run_id), "--history-dir", str(history_dir), "--yes"]
    )
    assert result.exit_code == 0
    assert undo_result.exit_code == 0
    assert second_undo.exit_code == 0
    assert "This run was already undone" in second_undo.output


def test_history_on_empty_catalog(tmp_path: Path) -> None:
    history_dir = tmp_path / "smart-janitor" / "history"
    history_dir.mkdir(parents=True)

    result = runner.invoke(app, ["history", "--history-dir", str(history_dir)])

    assert result.exit_code == 0
    assert "No previous runs" in result.output


def test_run_aborts_when_confirmation_declined(cli_setup: tuple[Path, Path, Path]) -> None:
    scan_dir, config, dest_dir = cli_setup
    result = runner.invoke(app, ["run", str(scan_dir), "--config", str(config)], input="n\n")

    assert result.exit_code == 1
    assert "Aborted" in result.output
    assert (scan_dir / "photo.jpg").exists()  # nothing moved
    assert not (dest_dir / "photo.jpg").exists()


def test_run_proceeds_with_yes_flag(cli_setup: tuple[Path, Path, Path]) -> None:
    scan_dir, config, dest_dir = cli_setup
    result = runner.invoke(
        app, ["run", str(scan_dir), "--config", str(config), "--yes"], input=""
    )

    assert result.exit_code == 0
    assert not (scan_dir / "photo.jpg").exists()
    assert (dest_dir / "photo.jpg").exists()


def test_run_rename_rule_end_to_end(tmp_path: Path) -> None:
    """A rename rule applied through the CLI renames the file in place."""
    scan_dir = tmp_path / "messy"
    scan_dir.mkdir()
    original = scan_dir / "Screenshot 2024-05-29 at 10.30.00.png"
    original.write_text("shot")

    config = tmp_path / "rules.yaml"
    config.write_text(
        r"""
version: 1
rules:
  - match:
      type: regex
      pattern: '^Screenshot.*\.png$'
    action:
      kind: rename
      pattern: '^Screenshot (\d{4}-\d{2}-\d{2}) at (\d{2}\.\d{2}\.\d{2})\.png$'
      replacement: 'screenshot_\1_\2.png'
"""
    )

    result = runner.invoke(app, ["run", str(scan_dir), "--config", str(config), "--yes"])

    assert result.exit_code == 0
    assert not original.exists()
    assert (scan_dir / "screenshot_2024-05-29_10.30.00.png").exists()


def test_plan_shows_rename_destination(tmp_path: Path) -> None:
    scan_dir = tmp_path / "messy"
    scan_dir.mkdir()
    (scan_dir / "report_final_v2.txt").write_text("x")

    config = tmp_path / "rules.yaml"
    config.write_text(
        r"""
version: 1
rules:
  - match:
      type: regex
      pattern: 'report'
    action:
      kind: rename
      pattern: '_final_v\d+'
      replacement: ''
"""
    )

    result = runner.invoke(app, ["plan", str(scan_dir), "--config", str(config)])

    assert result.exit_code == 0
    assert "report.txt" in result.output


def test_init_sample_config_is_valid(tmp_path: Path) -> None:
    """The generated sample config must load without errors."""
    output = tmp_path / "rules.yaml"
    result = runner.invoke(app, ["init", "--output", str(output)])
    assert result.exit_code == 0

    rules = load_config(output)
    assert len(rules) == 5  # 4 original rules + rename example
