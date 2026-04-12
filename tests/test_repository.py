from __future__ import annotations

from datetime import date

import pytest

from habit_tracker_cli.models import FrequencyType
from habit_tracker_cli.repository import DuplicateHabitError


def test_create_and_list_habits(service) -> None:
    daily = service.repository.create_habit("Read", FrequencyType.DAILY)
    weekly = service.repository.create_habit("Gym", FrequencyType.WEEKLY, weekdays=(0, 2, 4))

    habits = service.repository.list_habits()

    assert [habit.name for habit in habits] == ["Gym", "Read"]
    assert daily.weekdays == ()
    assert weekly.weekdays == (0, 2, 4)


def test_duplicate_habits_are_rejected(service) -> None:
    service.repository.create_habit("Read", FrequencyType.DAILY)

    with pytest.raises(DuplicateHabitError):
        service.repository.create_habit("  read  ", FrequencyType.DAILY)


def test_add_completion_is_idempotent(service) -> None:
    habit = service.repository.create_habit("Read", FrequencyType.DAILY)

    first_insert = service.repository.add_completion(habit.id, date(2026, 4, 10))
    second_insert = service.repository.add_completion(habit.id, date(2026, 4, 10))

    assert first_insert is True
    assert second_insert is False


def test_get_habit_by_name_is_case_insensitive_and_trim_safe(service) -> None:
    service.repository.create_habit("Read 20 min", FrequencyType.DAILY)

    found = service.repository.get_habit_by_name("  read 20 min ")

    assert found is not None
    assert found.name == "Read 20 min"
