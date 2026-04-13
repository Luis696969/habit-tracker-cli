# Changelog

## 0.1.2 - 2026-04-13

- Added `undo NAME` to remove today's completion idempotently.
- Added `delete NAME` to hard-delete habits and their related history.
- Integrated `undo` and `delete` into the interactive shell, help pages, and habit-name completion.

## 0.1.0 - 2026-04-13

- First public release.
- Added a richer interactive shell with persistent header, help, manual pages, and tab completion.
- Added the `clear-data` maintenance command.
- Switched app storage to cross-platform path handling with `platformdirs`.
- Added repository docs, issue templates, and CI scaffolding for GitHub publication.
