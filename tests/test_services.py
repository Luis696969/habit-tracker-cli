from __future__ import annotations

from datetime import date

import pytest

from habit_tracker_cli.services import HabitNotFoundError


def test_get_today_habits_returns_due_items(service) -> None:
    service.add_habit("Read", daily=True, days_csv=None)
    service.add_habit("Gym", daily=False, days_csv="mon,wed,fri")

    habits = service.get_today_habits(target_date=date(2026, 4, 13))

    assert [item.habit.name for item in habits] == ["Gym", "Read"]


def test_mark_done_is_idempotent(service) -> None:
    service.add_habit("Read", daily=True, days_csv=None)

    _, first = service.mark_done("Read", completed_on=date(2026, 4, 12))
    _, second = service.mark_done("Read", completed_on=date(2026, 4, 12))

    assert first is True
    assert second is False


def test_undo_done_removes_existing_completion(service) -> None:
    service.add_habit("Read", daily=True, days_csv=None)
    service.mark_done("Read", completed_on=date(2026, 4, 12))

    _, removed = service.undo_done("Read", completed_on=date(2026, 4, 12))

    assert removed is True
    assert service.repository.get_completion_dates(1) == set()


def test_undo_done_is_idempotent_when_completion_is_missing(service) -> None:
    service.add_habit("Read", daily=True, days_csv=None)

    _, removed = service.undo_done("Read", completed_on=date(2026, 4, 12))

    assert removed is False


def test_delete_habit_removes_it(service) -> None:
    service.add_habit("Read", daily=True, days_csv=None)

    deleted = service.delete_habit("Read")

    assert deleted.name == "Read"
    assert service.list_habits() == []


def test_delete_habit_allows_recreating_the_same_name(service) -> None:
    service.add_habit("Read", daily=True, days_csv=None)

    service.delete_habit("Read")
    recreated = service.add_habit("Read", daily=True, days_csv=None)

    assert recreated.name == "Read"


def test_delete_habit_raises_for_missing_name(service) -> None:
    with pytest.raises(HabitNotFoundError):
        service.delete_habit("Missing")


def test_daily_streak_counts_consecutive_days(service) -> None:
    service.add_habit("Read", daily=True, days_csv=None)
    service.mark_done("Read", completed_on=date(2026, 4, 10))
    service.mark_done("Read", completed_on=date(2026, 4, 11))
    service.mark_done("Read", completed_on=date(2026, 4, 12))

    _, streak = service.get_streak("Read", as_of=date(2026, 4, 12))

    assert streak == 3


def test_weekly_streak_ignores_unscheduled_days(service) -> None:
    service.add_habit("Gym", daily=False, days_csv="mon,wed,fri")
    service.mark_done("Gym", completed_on=date(2026, 4, 13))
    service.mark_done("Gym", completed_on=date(2026, 4, 15))

    _, streak = service.get_streak("Gym", as_of=date(2026, 4, 16))

    assert streak == 2


def test_weekly_report_summarizes_counts(service) -> None:
    service.add_habit("Read", daily=True, days_csv=None)
    service.add_habit("Gym", daily=False, days_csv="mon,wed,fri")

    for day in (13, 14, 15):
        service.mark_done("Read", completed_on=date(2026, 4, day))
    for day in (13, 15):
        service.mark_done("Gym", completed_on=date(2026, 4, day))

    report = service.get_weekly_report(as_of=date(2026, 4, 15))

    read_row = next(row for row in report.rows if row.habit.name == "Read")
    gym_row = next(row for row in report.rows if row.habit.name == "Gym")

    assert report.week_start == date(2026, 4, 13)
    assert report.week_end == date(2026, 4, 19)
    assert read_row.completed_count == 3
    assert read_row.scheduled_count == 7
    assert gym_row.completed_count == 2
    assert gym_row.scheduled_count == 3
