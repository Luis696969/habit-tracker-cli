from __future__ import annotations

from datetime import date

from habit_tracker_cli.dates import (
    end_of_week,
    latest_scheduled_on_or_before,
    ordered_intersection,
    parse_days_csv,
    previous_scheduled_date,
    scheduled_dates_between,
    start_of_week,
    today_local,
)
from habit_tracker_cli.models import FrequencyType, Habit, HabitWithStatus, WeeklyHabitReport, WeeklyReport
from habit_tracker_cli.repository import DuplicateHabitError, HabitRepository


class HabitTrackerError(Exception):
    """Base application error."""


class HabitNotFoundError(HabitTrackerError):
    """Raised when a habit name cannot be resolved."""


class HabitValidationError(HabitTrackerError):
    """Raised when user input is invalid."""


class HabitService:
    def __init__(self, repository: HabitRepository) -> None:
        self.repository = repository

    def close(self) -> None:
        self.repository.close()

    def add_habit(self, name: str, *, daily: bool, days_csv: str | None) -> Habit:
        if daily and days_csv:
            raise HabitValidationError("Use either --daily or --days, not both.")
        if not daily and not days_csv:
            raise HabitValidationError("Choose one schedule: --daily or --days.")

        if daily:
            frequency_type = FrequencyType.DAILY
            weekdays: tuple[int, ...] = ()
        else:
            frequency_type = FrequencyType.WEEKLY
            try:
                weekdays = parse_days_csv(days_csv or "")
            except ValueError as exc:
                raise HabitValidationError(str(exc)) from exc

        try:
            return self.repository.create_habit(name=name, frequency_type=frequency_type, weekdays=weekdays)
        except ValueError as exc:
            raise HabitValidationError(str(exc)) from exc
        except DuplicateHabitError as exc:
            raise HabitValidationError(str(exc)) from exc

    def list_habits(self) -> list[Habit]:
        return self.repository.list_habits()

    def list_habit_names(self) -> list[str]:
        return [habit.name for habit in self.list_habits()]

    def get_today_habits(self, target_date: date | None = None) -> list[HabitWithStatus]:
        target_date = target_date or today_local()
        habits = self.repository.list_habits()
        completion_map = self.repository.get_completion_map(target_date, target_date)
        completed_habit_ids = set(completion_map.keys())

        due_habits: list[HabitWithStatus] = []
        for habit in habits:
            if habit.is_daily or target_date.weekday() in habit.weekdays:
                due_habits.append(
                    HabitWithStatus(
                        habit=habit,
                        target_date=target_date,
                        completed=habit.id in completed_habit_ids,
                    )
                )
        return due_habits

    def mark_done(self, name: str, completed_on: date | None = None) -> tuple[Habit, bool]:
        completed_on = completed_on or today_local()
        try:
            habit = self.repository.get_habit_by_name(name)
        except ValueError as exc:
            raise HabitValidationError(str(exc)) from exc
        if habit is None:
            raise HabitNotFoundError(f"Habit '{name.strip()}' was not found.")

        inserted = self.repository.add_completion(habit.id, completed_on)
        return habit, inserted

    def get_streak(self, name: str, as_of: date | None = None) -> tuple[Habit, int]:
        as_of = as_of or today_local()
        try:
            habit = self.repository.get_habit_by_name(name)
        except ValueError as exc:
            raise HabitValidationError(str(exc)) from exc
        if habit is None:
            raise HabitNotFoundError(f"Habit '{name.strip()}' was not found.")

        anchor_date = latest_scheduled_on_or_before(habit, as_of)
        if anchor_date is None:
            return habit, 0

        completion_dates = self.repository.get_completion_dates(habit.id, end_date=anchor_date)
        if anchor_date not in completion_dates:
            return habit, 0

        streak = 0
        current_date: date | None = anchor_date
        while current_date is not None and current_date in completion_dates:
            streak += 1
            current_date = previous_scheduled_date(habit, current_date)

        return habit, streak

    def get_weekly_report(self, as_of: date | None = None) -> WeeklyReport:
        as_of = as_of or today_local()
        week_start = start_of_week(as_of)
        week_end = end_of_week(as_of)
        habits = self.repository.list_habits()
        completion_map = self.repository.get_completion_map(week_start, week_end)

        rows: list[WeeklyHabitReport] = []
        for habit in habits:
            scheduled_dates = scheduled_dates_between(habit, week_start, week_end)
            completed_dates = ordered_intersection(scheduled_dates, completion_map.get(habit.id, set()))
            rows.append(
                WeeklyHabitReport(
                    habit=habit,
                    scheduled_dates=scheduled_dates,
                    completed_dates=completed_dates,
                )
            )

        return WeeklyReport(week_start=week_start, week_end=week_end, rows=tuple(rows))
