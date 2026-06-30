from pathlib import Path

import pytest
from typer.testing import CliRunner

from smart_janitor.cli import app

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
    result = runner.invoke(app, ["run", str(scan_dir), "--config", str(config)])
    assert result.exit_code == 0
    assert not (scan_dir / "photo.jpg").exists()
    assert (dest_dir / "photo.jpg").exists()


def test_run_dry_run_without_moving_files(cli_setup: tuple[Path, Path, Path]) -> None:
    scan_dir, config, dest_dir = cli_setup
    result = runner.invoke(app, ["run", str(scan_dir), "--config", str(config), "--dry-run"])
    assert result.exit_code == 0
    assert (scan_dir / "photo.jpg").exists()
    assert not (dest_dir / "photo.jpg").exists()
