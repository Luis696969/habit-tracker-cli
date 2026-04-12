from __future__ import annotations

import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
TEST_TEMP_ROOT = PROJECT_ROOT / ".tmp_pytest"

TEST_TEMP_ROOT.mkdir(exist_ok=True)
os.environ["TMP"] = str(TEST_TEMP_ROOT)
os.environ["TEMP"] = str(TEST_TEMP_ROOT)
tempfile.tempdir = str(TEST_TEMP_ROOT)

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from habit_tracker_cli.db import get_connection
from habit_tracker_cli.repository import HabitRepository
from habit_tracker_cli.services import HabitService


@pytest.fixture()
def app_home() -> Path:
    run_dir = TEST_TEMP_ROOT / f"run-{uuid.uuid4().hex}"
    run_dir.mkdir(parents=True, exist_ok=False)
    try:
        app_root = run_dir / "app-home"
        app_root.mkdir(parents=True, exist_ok=True)
        yield app_root
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


@pytest.fixture()
def db_path(app_home: Path) -> Path:
    return app_home / "data" / "habit_tracker.db"


@pytest.fixture()
def service(db_path: Path) -> HabitService:
    app_service = HabitService(HabitRepository(get_connection(db_path)))
    yield app_service
    app_service.close()


@pytest.fixture()
def cli_env(app_home: Path) -> dict[str, str]:
    return {"HABIT_TRACKER_HOME": str(app_home)}
