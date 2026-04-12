import sqlite3
from pathlib import Path

from habit_tracker_cli.paths import resolve_app_paths

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    frequency_type TEXT NOT NULL CHECK (frequency_type IN ('daily', 'weekly')),
    created_at TEXT NOT NULL,
    archived_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS habit_days (
    id INTEGER PRIMARY KEY,
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    UNIQUE (habit_id, weekday)
);

CREATE TABLE IF NOT EXISTS completions (
    id INTEGER PRIMARY KEY,
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    completed_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (habit_id, completed_on)
);

CREATE INDEX IF NOT EXISTS idx_completions_habit_date
ON completions (habit_id, completed_on);
"""


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    connection.commit()


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    app_paths = resolve_app_paths(db_path)
    resolved_path = app_paths.db_path
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    initialize_database(connection)
    return connection
