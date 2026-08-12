# Smart Janitor

CLI that tidies messy folders using declarative YAML rules — match files, move them, and undo safely.

[![CI](https://github.com/jakublvndsky/smart-janitor/actions/workflows/ci.yml/badge.svg)](https://github.com/jakublvndsky/smart-janitor/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jakublvndsky/smart-janitor/graph/badge.svg?token=0ONIU5ABF3)](https://codecov.io/gh/jakublvndsky/smart-janitor)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

- Declarative, versioned rules in YAML
- Match by extension, regex, size, or age
- Actions: `move_to`, `archive`, and `rename` (schema-ready; rename not executed yet)
- `plan` and `--dry-run` to preview before touching files
- Collision handling: `skip`, `rename`, or `overwrite`
- Run history with per-run `undo`
- Rich tables and summaries in the terminal

## Installation

Requires [uv](https://docs.astral.sh/uv/) and Python ≥ 3.12.

```bash
git clone https://github.com/jakublvndsky/smart-janitor.git
cd smart-janitor
uv sync
```

Run via `uv run smart-janitor …`, or install editable:

```bash
uv pip install -e .
```

## Quick start

```bash
uv run smart-janitor init
uv run smart-janitor plan ~/Downloads
uv run smart-janitor run ~/Downloads --dry-run
uv run smart-janitor run ~/Downloads
uv run smart-janitor history
uv run smart-janitor undo 20260812-153045   # use an ID from history
```

## Commands

### `init`

Generate a sample `rules.yaml`.

| Option | Default | Description |
| --- | --- | --- |
| `-o`, `--output` | `rules.yaml` | Output path (fails if the file already exists) |

### `plan PATH`

Preview planned moves without changing anything.

| Option | Default | Description |
| --- | --- | --- |
| `-c`, `--config` | `rules.yaml` | Rules file |
| `--recursive` / `--no-recursive` | recursive | Scan subdirectories |
| `--include-hidden` / `--no-include-hidden` | no | Include dotfiles |

### `run PATH`

Scan, plan, and execute moves. Non-dry runs are saved under `~/.smart-janitor/history`.

| Option | Default | Description |
| --- | --- | --- |
| `-c`, `--config` | `rules.yaml` | Rules file |
| `--recursive` / `--no-recursive` | recursive | Scan subdirectories |
| `--include-hidden` / `--no-include-hidden` | no | Include dotfiles |
| `-dr`, `--dry-run` | off | Simulate without writing |
| `-oc`, `--on-collision` | `skip` | `skip`, `rename`, or `overwrite` |
| `-hd`, `--history-dir` | `~/.smart-janitor/history` | Where to store run records |

### `history`

List previous runs.

| Option | Default | Description |
| --- | --- | --- |
| `-hd`, `--history-dir` | `~/.smart-janitor/history` | History directory |

### `undo RUN_ID`

Invert a previous run (moves files back). Requires a run ID from `history`.

| Option | Default | Description |
| --- | --- | --- |
| `-hd`, `--history-dir` | `~/.smart-janitor/history` | History directory |
| `-dr`, `--dry-run` | off | Simulate without writing |
| `-oc`, `--on-collision` | `skip` | `skip`, `rename`, or `overwrite` |

## Configuration

Rules live in a YAML file with this shape:

```yaml
version: 1
rules:
  - match: { ... }
    action: { ... }
```

First matching rule wins per file.

### Match types

**`extension`** — extension without a leading dot (normalized to lowercase):

```yaml
match:
  type: extension
  pattern: pdf
```

**`regex`** — Python regex against the filename:

```yaml
match:
  type: regex
  pattern: '^Screenshot.*\.png$'
```

**`size`** — compare file size (`operator`: `lt` | `gt` | `eq`; `unit`: `B` | `KB` | `MB` | `GB`):

```yaml
match:
  type: size
  threshold: 500
  unit: MB
  operator: gt
```

**`age`** — files older than N days (by mtime; `older_than_days` ≥ 0):

```yaml
match:
  type: age
  older_than_days: 30
```

### Actions

**`move_to`** — move the file into `dst` (keeps the original name):

```yaml
action:
  kind: move_to
  dst: ~/Pictures
```

**`archive`** — same destination semantics as `move_to` (intended for archive folders):

```yaml
action:
  kind: archive
  dst: ~/Documents/Archive
```

**`rename`** — rules using rename are currently skipped without warning:

```yaml
action:
  kind: rename
  pattern: "(.*)"
  replacement: "\\1_sorted"
```

### Full example

```yaml
version: 1
rules:
  - match:
      type: age
      older_than_days: 30
    action:
      kind: archive
      dst: ~/Documents/Archive

  - match:
      type: extension
      pattern: jpg
    action:
      kind: move_to
      dst: ~/Pictures

  - match:
      type: size
      threshold: 500
      unit: MB
      operator: gt
    action:
      kind: move_to
      dst: /Volumes/External/LargeFiles

  - match:
      type: regex
      pattern: "^Screenshot.*\\.png$"
    action:
      kind: move_to
      dst: ~/Pictures/Screenshots
```

`smart-janitor init` writes a similar sample.

## Development

```bash
uv sync --group dev
uv run pytest
uv run pytest --cov=smart_janitor
uv run ruff check
uv run mypy src/ tests/
```

Optional hooks:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

CI runs the same checks on Ubuntu and macOS for Python 3.12 and 3.13.

## License

MIT — see [LICENSE](LICENSE).
