# Configuration Reference

Smart Janitor reads declarative rules from a YAML file (default: `rules.yaml`).
Rules are evaluated in order for every scanned file — the **first rule whose
match condition is satisfied wins**, so put more specific rules first.

## Top-level schema

```yaml
version: 1
rules:
  - match:
      type: extension
      pattern: pdf
    action:
      kind: move_to
      dst: ~/Documents/PDFs
```

| Field     | Type  | Required | Description                              |
| --------- | ----- | -------- | ---------------------------------------- |
| `version` | int   | no       | Config schema version (currently `1`).   |
| `rules`   | list  | yes      | Ordered list of rules (may be empty).    |

## Match conditions

A rule matches a file when **at least one** condition is true. Each condition
is discriminated by its `type` field.

### `extension` — match by file extension

```yaml
match:
  type: extension
  pattern: jpg
```

- `pattern` is normalized: leading dots are stripped and it is lowercased,
  so `.JPG`, `JPG` and `jpg` are equivalent.

### `regex` — match by regular expression on the file name

```yaml
match:
  type: regex
  pattern: "^Screenshot.*\\.png$"
```

- `pattern` is compiled with Python's `re` and searched (not anchored) against
  the file name unless you anchor it yourself with `^` / `$`.
- Invalid patterns are rejected at config-load time with a clear error.

### `size` — match by file size

```yaml
match:
  type: size
  threshold: 500
  unit: MB
  operator: gt
```

- `threshold` is a number; `unit` is one of `B`, `KB`, `MB`, `GB`
  (binary multiples: 1 KB = 1024 B).
- `operator` is one of:
  - `lt` — file size strictly smaller than the threshold
  - `eq` — file size exactly equal to the threshold
  - `gt` — file size strictly greater than the threshold

### `age` — match by modification time

```yaml
match:
  type: age
  older_than_days: 30
```

- Matches files whose last modification is **strictly more than**
  `older_than_days` days ago (`older_than_days` must be `>= 0`).
- Comparison is done in UTC.

## Actions

### `move_to` — move the file into a directory

```yaml
action:
  kind: move_to
  dst: ~/Downloads/Sorted
```

- The destination directory is created if it does not exist.
- Collisions with existing files are handled according to the
  `--on-collision` strategy (`skip` (default), `rename`, `overwrite`).
- `~` is expanded to the home directory.

### `archive` — same as `move_to` (semantic alias)

```yaml
action:
  kind: archive
  dst: ~/Archive
```

Archive moves are tracked identically to `move_to` moves in run history and
can be undone.

### `rename` — rename the file in place

```yaml
action:
  kind: rename
  pattern: "^Screenshot (\\d{4}-\\d{2}-\\d{2}) at (\\d{2}\\.\\d{2}\\.\\d{2})\\.png$"
  replacement: "screenshot_\\1_\\2.png"
```

- The file stays in its current directory; only the name changes.
- If `pattern` matches the **entire** file name, `replacement` is used
  verbatim (backreferences like `\1` are supported).
- Otherwise `replacement` is substituted into the name wherever `pattern`
  matches (standard `re.sub` semantics).
- The `pattern` is validated at config-load time; a rename that would
  produce an empty name is reported as an error during planning.

## Example config

```yaml
version: 1
rules:
  # 1. Screenshots get renamed and moved to a dedicated folder
  - match:
      type: regex
      pattern: "^Screenshot (\\d{4}-\\d{2}-\\d{2}) at (\\d{2}\\.\\d{2}\\.\\d{2})\\.png$"
    action:
      kind: rename
      pattern: "^Screenshot (\\d{4}-\\d{2}-\\d{2}) at (\\d{2}\\.\\d{2}\\.\\d{2})\\.png$"
      replacement: "screenshot_\\1_\\2.png"

  # 2. PDFs older than 30 days go to the archive
  - match:
      type: age
      older_than_days: 30
    action:
      kind: archive
      dst: ~/Documents/Archive

  # 3. Files over 500 MB go to an external drive
  - match:
      type: size
      threshold: 500
      unit: MB
      operator: gt
    action:
      kind: move_to
      dst: /Volumes/External/LargeFiles
```

> Rule order matters: the first matching rule wins, so specific rules
> (e.g. a regex for screenshots) should come before broad ones
> (e.g. "everything older than 30 days").
