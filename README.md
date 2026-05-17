# Smart Janitor

A CLI tool that tidies up messy folders based on declarative YAML rules.
Match files by extension, regex, size, or age — then move, rename, or archive them safely with a built-in dry-run and undo.

## Features

- 📋 Declarative rules in YAML
- 🔍 Match by extension, regex, file size, or modification time
- 🧪 `--dry-run` mode — preview before touching anything
- ↩️ Full operation history with `undo`
- 🎨 Pretty terminal output (Rich)
- 🪶 Zero config to start: `smart-janitor init`

## Installation

```bash
uv pip install smart-janitor
```

Or from source:

```bash
git clone https://github.com/<your-username>/smart-janitor.git
cd smart-janitor
uv sync
uv pip install -e .
```

## Quick start

```bash
# Generate a sample config in the current folder
smart-janitor init

# Preview what would happen
smart-janitor plan ~/Downloads --config rules.yaml

# Run for real
smart-janitor run ~/Downloads --config rules.yaml

# Oops — undo the last run
smart-janitor undo
```

## Configuration

Rules live in a YAML file. Example:

```yaml
rules:
  - name: "Archive old PDFs"
    match:
      extension: pdf
      older_than_days: 30
    action:
      move_to: ~/Documents/Archive/PDFs

  - name: "Screenshots to Pictures"
    match:
      regex: "^Screenshot.*\\.png$"
    action:
      move_to: ~/Pictures/Screenshots
```

See [docs/configuration.md](docs/configuration.md) for the full reference. *(TBD)*

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check
uv run mypy src/
```

## License

MIT — see [LICENSE](LICENSE).

## Status

🚧 Early development. Not yet on PyPI.