from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class FrequencyType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass(frozen=True, slots=True)
class Habit:
    id: int
    name: str
    normalized_name: str
    frequency_type: FrequencyType
    created_at: datetime
    weekdays: tuple[int, ...] = ()

    @property
    def is_daily(self) -> bool:
        return self.frequency_type == FrequencyType.DAILY


@dataclass(frozen=True, slots=True)
class HabitWithStatus:
    habit: Habit
    target_date: date
    completed: bool


@dataclass(frozen=True, slots=True)
class WeeklyHabitReport:
    habit: Habit
    scheduled_dates: tuple[date, ...]
    completed_dates: tuple[date, ...]

    @property
    def scheduled_count(self) -> int:
        return len(self.scheduled_dates)

    @property
    def completed_count(self) -> int:
        return len(self.completed_dates)

    @property
    def missed_count(self) -> int:
        return self.scheduled_count - self.completed_count

    @property
    def completion_rate(self) -> float:
        if self.scheduled_count == 0:
            return 0.0
        return self.completed_count / self.scheduled_count


@dataclass(frozen=True, slots=True)
class WeeklyReport:
    week_start: date
    week_end: date
    rows: tuple[WeeklyHabitReport, ...]

    @property
    def total_scheduled(self) -> int:
        return sum(row.scheduled_count for row in self.rows)

    @property
    def total_completed(self) -> int:
        return sum(row.completed_count for row in self.rows)
