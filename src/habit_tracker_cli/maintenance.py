import shutil
from dataclasses import dataclass
from pathlib import Path

from habit_tracker_cli.paths import AppPaths, resolve_app_paths


@dataclass(frozen=True, slots=True)
class PathStatus:
    path: Path
    exists: bool
    kind: str


def _path_kind(path: Path) -> str:
    if path.exists():
        if path.is_dir():
            return "dir"
        return "file"
    if path.suffix:
        return "file"
    return "dir"


def describe_data_paths(app_paths: AppPaths | None = None) -> tuple[PathStatus, ...]:
    resolved_paths = app_paths or resolve_app_paths()
    return tuple(
        PathStatus(path=path, exists=path.exists(), kind=_path_kind(path))
        for path in resolved_paths.clear_targets()
    )


def clear_data_paths(app_paths: AppPaths | None = None) -> tuple[Path, ...]:
    deleted_paths: list[Path] = []
    for item in describe_data_paths(app_paths):
        path = item.path
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=False)
        else:
            path.unlink(missing_ok=True)
        deleted_paths.append(path)
    return tuple(deleted_paths)
