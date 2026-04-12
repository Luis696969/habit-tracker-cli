from __future__ import annotations

from pathlib import Path

from habit_tracker_cli.paths import resolve_app_paths


def test_resolve_app_paths_uses_custom_home(monkeypatch, app_home) -> None:
    monkeypatch.setenv("HABIT_TRACKER_HOME", str(app_home))
    monkeypatch.delenv("HABIT_TRACKER_DB_PATH", raising=False)

    paths = resolve_app_paths()

    assert paths.data_dir == app_home / "data"
    assert paths.state_dir == app_home / "state"
    assert paths.config_dir == app_home / "config"
    assert paths.cache_dir == app_home / "cache"
    assert paths.db_path == app_home / "data" / "habit_tracker.db"
    assert paths.history_path == app_home / "state" / "shell_history.txt"


def test_resolve_app_paths_respects_db_override(monkeypatch, app_home) -> None:
    override_path = app_home / "custom" / "db.sqlite3"
    monkeypatch.setenv("HABIT_TRACKER_HOME", str(app_home))
    monkeypatch.setenv("HABIT_TRACKER_DB_PATH", str(override_path))

    paths = resolve_app_paths()

    assert paths.db_path == override_path
