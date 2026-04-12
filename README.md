# habit_tracker_cli

`habit_tracker_cli` is a small cross-platform habit tracker for the terminal. It keeps the command-line workflow simple, stores data locally in SQLite, and includes a lightweight interactive shell for day-to-day use.

Public command:

```bash
habit-tracker
```

## Features

- Add daily habits or habits scheduled on specific weekdays
- Mark habits as done for today
- Show habits due today
- Check the current streak for one habit
- Show a weekly report
- Use an interactive shell with help, manual pages, and tab completion
- Clear local app data safely with `clear-data`

## Installation

### Windows

Recommended: `pipx` from PowerShell or Windows Terminal. `pipx` keeps the app isolated and avoids cluttering the main Python environment.

Install from source today:

```powershell
pipx install .
```

Future PyPI install target:

```powershell
pipx install habit-tracker-cli
```

### Linux

Recommended: `pipx`.

Install from source today:

```bash
pipx install .
```

Future PyPI install target:

```bash
pipx install habit-tracker-cli
```

### Development install from source

```bash
pip install -e .[dev]
python -m pytest
```

## Usage

```bash
habit-tracker add "Read 20 min" --daily
habit-tracker add "Go to the gym" --days mon,wed,fri
habit-tracker list
habit-tracker today
habit-tracker done "Read 20 min"
habit-tracker streak "Read 20 min"
habit-tracker report
habit-tracker report --week
```

`report` and `report --week` are equivalent in the current version.

## Interactive shell

Start it explicitly:

```bash
habit-tracker shell
```

Running `habit-tracker` with no subcommand also enters the shell.

Prompt:

```text
habit>
```

Shell commands:

- `add`
- `list`
- `today`
- `done`
- `streak`
- `report`
- `help`
- `man`
- `clear`
- `clear-data`
- `exit`
- `q`

## Data storage

The app uses `platformdirs` for predictable per-user storage.

Typical locations:

| OS | Data location |
| --- | --- |
| Windows | `%LOCALAPPDATA%\habit_tracker_cli\` |
| Linux | `$XDG_DATA_HOME/habit_tracker_cli/` or `~/.local/share/habit_tracker_cli/` |

Shell state and history live in the matching per-user state/config directories for the same app name.

Optional overrides:

```bash
HABIT_TRACKER_DB_PATH=/custom/path/habit_tracker.db
HABIT_TRACKER_HOME=/custom/app-home
```

## Clear app data

```bash
habit-tracker clear-data
habit-tracker clear-data --yes
```

`clear-data` shows the exact paths it plans to remove and asks for confirmation unless `--yes` is used.

## Uninstall

If you installed with `pipx`:

```bash
pipx uninstall habit-tracker-cli
```

If you installed from source in editable mode:

```bash
pip uninstall habit_tracker_cli
```

There is intentionally no built-in self-uninstall command. Uninstall remains a manual step for safety.

## GitHub and PyPI readiness

The repository is set up for GitHub publication now and for straightforward future PyPI publication later.

Suggested future release flow:

```bash
python -m build
python -m twine check dist/*
```

When PyPI trusted publishing is configured, releases can be connected to an upload workflow. Until then, manual publishing is the safest option.

## License

MIT
