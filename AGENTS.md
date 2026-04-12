# AGENTS

## Repo intent

`habit_tracker_cli` is a small cross-platform Python CLI for habit tracking. Keep it simple, well-tested, and friendly to both Windows and Linux terminals.

## Working rules

- Reuse the existing architecture: CLI layer, service layer, repository layer, and small support modules.
- Do not rewrite the app from scratch.
- Prefer small patches over large refactors.
- Keep the public command `habit-tracker` stable.
- Keep dependencies minimal and justify any new one in docs or PR notes.
- Do not introduce self-uninstall behavior; uninstall should remain a manual user action.

## Verification

- Install for development with `pip install -e .[dev]`
- Run tests with `python -m pytest`
- When packaging or docs change, also run `python -m build`
- When changing shell behavior, verify both direct commands and `habit-tracker shell`
