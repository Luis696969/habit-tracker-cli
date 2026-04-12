from __future__ import annotations

from habit_tracker_cli.maintenance import (
    clear_data_paths,
    describe_data_paths,
)
from habit_tracker_cli.paths import ensure_parent_directories, resolve_app_paths


def test_clear_data_paths_deletes_known_files(monkeypatch, app_home) -> None:
    monkeypatch.setenv("HABIT_TRACKER_HOME", str(app_home))
    paths = resolve_app_paths()
    ensure_parent_directories(paths)
    paths.db_path.write_text("db", encoding="utf-8")
    paths.history_path.write_text("history", encoding="utf-8")
    paths.state_path.write_text("{}", encoding="utf-8")
    (paths.cache_dir / "cache.tmp").write_text("cache", encoding="utf-8")

    deleted = clear_data_paths(paths)

    assert paths.db_path in deleted
    assert paths.history_path in deleted
    assert not paths.data_dir.exists()
    assert not paths.state_dir.exists()
    assert not paths.cache_dir.exists()


def test_describe_data_paths_marks_existing_and_missing(monkeypatch, app_home) -> None:
    monkeypatch.setenv("HABIT_TRACKER_HOME", str(app_home))
    paths = resolve_app_paths()
    ensure_parent_directories(paths)
    paths.db_path.write_text("db", encoding="utf-8")

    statuses = describe_data_paths(paths)

    db_status = next(item for item in statuses if item.path == paths.db_path)
    history_status = next(item for item in statuses if item.path == paths.history_path)
    assert db_status.exists is True
    assert history_status.exists is False
