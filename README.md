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

# Run for real (confirms before moving; add --yes to skip the prompt)
smart-janitor run ~/Downloads --config rules.yaml

# Oops — undo the last run (list runs first to find its ID)
smart-janitor history
smart-janitor undo 20240101-120000
```

## Configuration

Rules live in a YAML file. Example:

```yaml
version: 1
rules:
  - match:
      type: extension
      pattern: pdf
    action:
      kind: move_to
      dst: ~/Documents/Archive/PDFs

  - match:
      type: regex
      pattern: "^Screenshot.*\\.png$"
    action:
      kind: move_to
      dst: ~/Pictures/Screenshots
```

Rules are evaluated in order — the first match wins. Matchers: `extension`,
`regex`, `size` (with `unit`/`operator`), and `age` (with `older_than_days`).
Actions: `move_to`, `archive`, and `rename` (regex rename in place).

See [docs/configuration.md](docs/configuration.md) for the full reference.

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