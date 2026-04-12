# Contributing

Thanks for contributing to `habit_tracker_cli`.

## Local setup

```bash
pip install -e .[dev]
python -m pytest
python -m build
```

## Guidelines

- Keep changes small and focused.
- Preserve the existing CLI commands and behavior unless the change explicitly updates them.
- Prefer standard-library solutions first; add dependencies only when they clearly improve portability or UX.
- Add or update tests for user-visible behavior.
- Keep Windows and Linux compatibility in mind.
- Keep uninstall behavior manual and explicit; do not add self-uninstall automation.

## Pull requests

- Include a short summary of what changed.
- Mention any cross-platform impact.
- Run `python -m pytest` before opening the PR.
- If packaging changed, also run `python -m build` and `python -m twine check dist/*`.
