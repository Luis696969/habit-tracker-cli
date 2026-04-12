from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, Sequence

from habit_tracker_cli.models import FrequencyType, Habit

WEEKDAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WEEKDAY_TO_INDEX = {name: idx for idx, name in enumerate(WEEKDAY_NAMES)}


def today_local() -> date:
    return date.today()


def now_local() -> datetime:
    return datetime.now().replace(microsecond=0)


def iso_date(value: date) -> str:
    return value.isoformat()


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def iso_datetime(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def clean_habit_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Habit name cannot be empty.")
    return cleaned


def normalize_habit_name(name: str) -> str:
    return clean_habit_name(name).lower()


def parse_days_csv(value: str) -> tuple[int, ...]:
    if not value.strip():
        raise ValueError("Provide at least one weekday in --days.")

    parsed: set[int] = set()
    invalid: list[str] = []

    for raw_day in value.split(","):
        token = raw_day.strip().lower()
        if not token:
            continue
        if token not in WEEKDAY_TO_INDEX:
            invalid.append(token)
            continue
        parsed.add(WEEKDAY_TO_INDEX[token])

    if invalid:
        valid = ", ".join(WEEKDAY_NAMES)
        raise ValueError(f"Invalid weekday value(s): {', '.join(invalid)}. Use: {valid}.")

    if not parsed:
        raise ValueError("Provide at least one valid weekday in --days.")

    return tuple(sorted(parsed))


def format_weekdays(weekdays: Sequence[int]) -> str:
    return ", ".join(WEEKDAY_NAMES[weekday] for weekday in weekdays)


def start_of_week(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def end_of_week(target_date: date) -> date:
    return start_of_week(target_date) + timedelta(days=6)


def is_habit_due_on(habit: Habit, target_date: date) -> bool:
    if habit.frequency_type == FrequencyType.DAILY:
        return True
    return target_date.weekday() in habit.weekdays


def scheduled_dates_between(habit: Habit, start_date: date, end_date: date) -> tuple[date, ...]:
    current = start_date
    scheduled: list[date] = []
    while current <= end_date:
        if is_habit_due_on(habit, current):
            scheduled.append(current)
        current += timedelta(days=1)
    return tuple(scheduled)


def latest_scheduled_on_or_before(habit: Habit, target_date: date) -> date | None:
    if habit.frequency_type == FrequencyType.DAILY:
        return target_date

    for offset in range(0, 7):
        candidate = target_date - timedelta(days=offset)
        if candidate.weekday() in habit.weekdays:
            return candidate
    return None


def previous_scheduled_date(habit: Habit, target_date: date) -> date | None:
    if habit.frequency_type == FrequencyType.DAILY:
        return target_date - timedelta(days=1)

    for offset in range(1, 8):
        candidate = target_date - timedelta(days=offset)
        if candidate.weekday() in habit.weekdays:
            return candidate
    return None


def ordered_intersection(left: Iterable[date], right: set[date]) -> tuple[date, ...]:
    return tuple(item for item in left if item in right)
