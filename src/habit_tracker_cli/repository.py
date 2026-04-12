from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, datetime

from habit_tracker_cli.dates import (
    clean_habit_name,
    iso_date,
    iso_datetime,
    normalize_habit_name,
    now_local,
    parse_iso_date,
    parse_iso_datetime,
)
from habit_tracker_cli.models import FrequencyType, Habit


class RepositoryError(Exception):
    """Base exception for repository operations."""


class DuplicateHabitError(RepositoryError):
    """Raised when a habit with the same normalized name already exists."""


class HabitRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def close(self) -> None:
        self.connection.close()

    def create_habit(
        self,
        name: str,
        frequency_type: FrequencyType,
        weekdays: tuple[int, ...] = (),
        created_at: datetime | None = None,
    ) -> Habit:
        cleaned_name = clean_habit_name(name)
        normalized_name = normalize_habit_name(cleaned_name)
        created_at = created_at or now_local()

        try:
            cursor = self.connection.execute(
                """
                INSERT INTO habits (name, normalized_name, frequency_type, created_at, archived_at)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (cleaned_name, normalized_name, frequency_type.value, iso_datetime(created_at)),
            )

            if frequency_type == FrequencyType.WEEKLY:
                self.connection.executemany(
                    """
                    INSERT INTO habit_days (habit_id, weekday)
                    VALUES (?, ?)
                    """,
                    [(cursor.lastrowid, weekday) for weekday in weekdays],
                )

            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise DuplicateHabitError(f"A habit named '{cleaned_name}' already exists.") from exc

        created = self.get_habit_by_name(cleaned_name)
        if created is None:
            raise RepositoryError("Habit was inserted but could not be reloaded.")
        return created

    def list_habits(self) -> list[Habit]:
        rows = self.connection.execute(
            """
            SELECT id, name, normalized_name, frequency_type, created_at
            FROM habits
            WHERE archived_at IS NULL
            ORDER BY normalized_name ASC
            """
        ).fetchall()
        return self._rows_to_habits(rows)

    def get_habit_by_name(self, name: str) -> Habit | None:
        normalized_name = normalize_habit_name(name)
        row = self.connection.execute(
            """
            SELECT id, name, normalized_name, frequency_type, created_at
            FROM habits
            WHERE normalized_name = ? AND archived_at IS NULL
            """,
            (normalized_name,),
        ).fetchone()

        if row is None:
            return None

        habits = self._rows_to_habits([row])
        return habits[0] if habits else None

    def add_completion(
        self,
        habit_id: int,
        completed_on: date,
        created_at: datetime | None = None,
    ) -> bool:
        created_at = created_at or now_local()
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO completions (habit_id, completed_on, created_at)
            VALUES (?, ?, ?)
            """,
            (habit_id, iso_date(completed_on), iso_datetime(created_at)),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def get_completion_dates(
        self,
        habit_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> set[date]:
        query = ["SELECT completed_on FROM completions WHERE habit_id = ?"]
        params: list[object] = [habit_id]

        if start_date is not None:
            query.append("AND completed_on >= ?")
            params.append(iso_date(start_date))
        if end_date is not None:
            query.append("AND completed_on <= ?")
            params.append(iso_date(end_date))

        rows = self.connection.execute(" ".join(query), tuple(params)).fetchall()
        return {parse_iso_date(row["completed_on"]) for row in rows}

    def get_completion_map(self, start_date: date, end_date: date) -> dict[int, set[date]]:
        rows = self.connection.execute(
            """
            SELECT habit_id, completed_on
            FROM completions
            WHERE completed_on >= ? AND completed_on <= ?
            """,
            (iso_date(start_date), iso_date(end_date)),
        ).fetchall()

        completion_map: dict[int, set[date]] = defaultdict(set)
        for row in rows:
            completion_map[row["habit_id"]].add(parse_iso_date(row["completed_on"]))
        return completion_map

    def _rows_to_habits(self, rows: list[sqlite3.Row]) -> list[Habit]:
        if not rows:
            return []

        habit_ids = [row["id"] for row in rows]
        weekdays_map = self._get_weekdays_map(habit_ids)

        habits: list[Habit] = []
        for row in rows:
            habits.append(
                Habit(
                    id=row["id"],
                    name=row["name"],
                    normalized_name=row["normalized_name"],
                    frequency_type=FrequencyType(row["frequency_type"]),
                    created_at=parse_iso_datetime(row["created_at"]),
                    weekdays=tuple(weekdays_map.get(row["id"], ())),
                )
            )
        return habits

    def _get_weekdays_map(self, habit_ids: list[int]) -> dict[int, list[int]]:
        placeholders = ", ".join("?" for _ in habit_ids)
        rows = self.connection.execute(
            f"""
            SELECT habit_id, weekday
            FROM habit_days
            WHERE habit_id IN ({placeholders})
            ORDER BY weekday ASC
            """,
            tuple(habit_ids),
        ).fetchall()

        weekdays_map: dict[int, list[int]] = defaultdict(list)
        for row in rows:
            weekdays_map[row["habit_id"]].append(row["weekday"])
        return weekdays_map
