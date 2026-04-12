from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "habit_tracker_cli"
APP_DISPLAY_NAME = "habit-tracker"
HOME_ENV_VAR = "HABIT_TRACKER_HOME"
DB_PATH_ENV_VAR = "HABIT_TRACKER_DB_PATH"
DB_FILE_NAME = "habit_tracker.db"
HISTORY_FILE_NAME = "shell_history.txt"
STATE_FILE_NAME = "shell_state.json"


@dataclass(frozen=True, slots=True)
class AppPaths:
    data_dir: Path
    config_dir: Path
    cache_dir: Path
    state_dir: Path
    db_path: Path
    history_path: Path
    state_path: Path

    def clear_targets(self) -> tuple[Path, ...]:
        ordered: list[Path] = [
            self.db_path,
            self.history_path,
            self.state_path,
            self.cache_dir,
            self.config_dir,
            self.state_dir,
            self.data_dir,
        ]
        unique_targets: list[Path] = []
        seen: set[Path] = set()
        for path in ordered:
            resolved = path.expanduser()
            if resolved not in seen:
                unique_targets.append(resolved)
                seen.add(resolved)
        return tuple(unique_targets)


def resolve_app_paths(db_path: str | Path | None = None) -> AppPaths:
    custom_home = os.getenv(HOME_ENV_VAR)
    if custom_home:
        root = Path(custom_home).expanduser()
        data_dir = root / "data"
        config_dir = root / "config"
        cache_dir = root / "cache"
        state_dir = root / "state"
    else:
        dirs = PlatformDirs(appname=APP_NAME, appauthor=False, roaming=False, ensure_exists=False)
        data_dir = Path(dirs.user_data_path)
        config_dir = Path(dirs.user_config_path)
        cache_dir = Path(dirs.user_cache_path)
        state_dir = Path(dirs.user_state_path)

    if db_path is not None:
        resolved_db_path = Path(db_path).expanduser()
    else:
        override_db_path = os.getenv(DB_PATH_ENV_VAR)
        if override_db_path:
            resolved_db_path = Path(override_db_path).expanduser()
        else:
            resolved_db_path = data_dir / DB_FILE_NAME

    return AppPaths(
        data_dir=data_dir,
        config_dir=config_dir,
        cache_dir=cache_dir,
        state_dir=state_dir,
        db_path=resolved_db_path,
        history_path=state_dir / HISTORY_FILE_NAME,
        state_path=state_dir / STATE_FILE_NAME,
    )


def ensure_parent_directories(paths: AppPaths) -> None:
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    paths.cache_dir.mkdir(parents=True, exist_ok=True)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.db_path.parent.mkdir(parents=True, exist_ok=True)
