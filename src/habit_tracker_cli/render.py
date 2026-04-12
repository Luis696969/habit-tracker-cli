from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from habit_tracker_cli.maintenance import PathStatus
from habit_tracker_cli.dates import format_weekdays, iso_date
from habit_tracker_cli.models import Habit, HabitWithStatus, WeeklyReport


def schedule_label(habit: Habit) -> str:
    if habit.is_daily:
        return "daily"
    return format_weekdays(habit.weekdays)


def render_habit_list(habits: list[Habit]) -> Table:
    table = Table(title="Habits")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Schedule", style="magenta")
    table.add_column("Created", style="green")

    for habit in habits:
        table.add_row(habit.name, schedule_label(habit), habit.created_at.date().isoformat())
    return table


def render_today(habits: list[HabitWithStatus]) -> Table:
    table = Table(title="Today")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Schedule", style="magenta")
    table.add_column("Status")

    for item in habits:
        status = "[green]done[/green]" if item.completed else "[yellow]pending[/yellow]"
        table.add_row(item.habit.name, schedule_label(item.habit), status)
    return table


def render_streak(habit: Habit, streak: int) -> Panel:
    body = Text()
    body.append(f"Habit: {habit.name}\n", style="cyan")
    body.append(f"Current streak: {streak}", style="green")
    return Panel.fit(body, title="Streak")


def render_weekly_report(report: WeeklyReport) -> Group:
    table = Table(title="Weekly Report")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Schedule", style="magenta")
    table.add_column("Completed", justify="right")
    table.add_column("Scheduled", justify="right")
    table.add_column("Missed", justify="right")
    table.add_column("Rate", justify="right")

    for row in report.rows:
        table.add_row(
            row.habit.name,
            schedule_label(row.habit),
            str(row.completed_count),
            str(row.scheduled_count),
            str(row.missed_count),
            f"{row.completion_rate:.0%}",
        )

    summary = Panel.fit(
        (
            f"Week: {iso_date(report.week_start)} to {iso_date(report.week_end)}\n"
            f"Total completed: {report.total_completed}/{report.total_scheduled}"
        ),
        title="Summary",
    )
    return Group(table, summary)


def render_path_statuses(title: str, statuses: tuple[PathStatus, ...]) -> Table:
    table = Table(title=title)
    table.add_column("Path", style="cyan")
    table.add_column("Kind", style="magenta", no_wrap=True)
    table.add_column("Status", style="green", no_wrap=True)

    for item in statuses:
        table.add_row(str(item.path), item.kind, "exists" if item.exists else "missing")
    return table
