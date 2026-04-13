from __future__ import annotations

import sys

import pytest
from typer.testing import CliRunner

from habit_tracker_cli import cli

try:
    from prompt_toolkit.document import Document

    PROMPT_TOOLKIT_TESTS = True
except ImportError:  # pragma: no cover
    PROMPT_TOOLKIT_TESTS = False

runner = CliRunner()


def test_add_daily_habit(cli_env) -> None:
    result = runner.invoke(cli.app, ["add", "Read 20 min", "--daily"], env=cli_env)

    assert result.exit_code == 0
    assert "Added habit" in result.stdout
    assert "Read 20 min" in result.stdout


def test_add_weekly_habit_with_spaces(cli_env) -> None:
    result = runner.invoke(cli.app, ["add", "Go to the gym", "--days", "mon,wed,fri"], env=cli_env)

    assert result.exit_code == 0
    assert "Go to the gym" in result.stdout


def test_add_requires_schedule(cli_env) -> None:
    result = runner.invoke(cli.app, ["add", "Read"], env=cli_env)

    assert result.exit_code == 1
    assert "Choose one schedule" in result.stderr


def test_done_and_streak_support_names_with_spaces(cli_env) -> None:
    add_result = runner.invoke(cli.app, ["add", "Morning Walk", "--daily"], env=cli_env)
    done_result = runner.invoke(cli.app, ["done", "Morning Walk"], env=cli_env)
    streak_result = runner.invoke(cli.app, ["streak", "Morning Walk"], env=cli_env)

    assert add_result.exit_code == 0
    assert done_result.exit_code == 0
    assert streak_result.exit_code == 0
    assert "Morning Walk" in done_result.stdout
    assert "Current streak" in streak_result.stdout


def test_undo_supports_names_with_spaces(cli_env) -> None:
    runner.invoke(cli.app, ["add", "Morning Walk", "--daily"], env=cli_env)
    runner.invoke(cli.app, ["done", "Morning Walk"], env=cli_env)

    result = runner.invoke(cli.app, ["undo", "Morning Walk"], env=cli_env)

    assert result.exit_code == 0
    assert "Removed today's completion" in result.stdout
    assert "Morning Walk" in result.stdout


def test_undo_without_existing_completion_is_idempotent(cli_env) -> None:
    runner.invoke(cli.app, ["add", "Read", "--daily"], env=cli_env)

    result = runner.invoke(cli.app, ["undo", "Read"], env=cli_env)

    assert result.exit_code == 0
    assert "was not marked as done for today" in result.stdout


def test_delete_removes_habit_from_list(cli_env) -> None:
    runner.invoke(cli.app, ["add", "Go to the gym", "--days", "mon,wed,fri"], env=cli_env)

    delete_result = runner.invoke(cli.app, ["delete", "Go to the gym"], env=cli_env)
    list_result = runner.invoke(cli.app, ["list"], env=cli_env)

    assert delete_result.exit_code == 0
    assert "Deleted habit" in delete_result.stdout
    assert "Go to the gym" in delete_result.stdout
    assert list_result.exit_code == 0
    assert "No habits found" in list_result.stdout


def test_delete_missing_habit_returns_exit_code_1(cli_env) -> None:
    result = runner.invoke(cli.app, ["delete", "Missing"], env=cli_env)

    assert result.exit_code == 1
    assert "was not found" in result.stderr


def test_list_today_and_report_commands(cli_env) -> None:
    runner.invoke(cli.app, ["add", "Read", "--daily"], env=cli_env)

    list_result = runner.invoke(cli.app, ["list"], env=cli_env)
    today_result = runner.invoke(cli.app, ["today"], env=cli_env)
    report_result = runner.invoke(cli.app, ["report", "--week"], env=cli_env)

    assert list_result.exit_code == 0
    assert today_result.exit_code == 0
    assert report_result.exit_code == 0
    assert "Habits" in list_result.stdout
    assert "Today" in today_result.stdout
    assert "Weekly Report" in report_result.stdout


def test_clear_data_command_deletes_app_data(cli_env, app_home) -> None:
    runner.invoke(cli.app, ["add", "Read", "--daily"], env=cli_env)

    result = runner.invoke(cli.app, ["clear-data", "--yes"], env=cli_env)

    assert result.exit_code == 0
    assert "App Data Paths" in result.stdout
    assert "Deleted" in result.stdout or "No app data was found" in result.stdout
    assert not (app_home / "data" / "habit_tracker.db").exists()


def test_shell_command_dispatches_existing_commands(cli_env) -> None:
    result = runner.invoke(
        cli.app,
        ["shell"],
        input='add "Read 20 min" --daily\nlist\nq\n',
        env=cli_env,
    )

    assert result.exit_code == 0
    assert "habit> " in result.stdout
    assert "Added habit" in result.stdout
    assert "Habits" in result.stdout
    assert "habit_tracker_cli" in result.stdout


def test_shell_supports_undo_and_delete(cli_env) -> None:
    result = runner.invoke(
        cli.app,
        ["shell"],
        input='add "Read 20 min" --daily\ndone "Read 20 min"\nundo "Read 20 min"\ndelete "Read 20 min"\nlist\nq\n',
        env=cli_env,
    )

    assert result.exit_code == 0
    assert "Removed today's completion" in result.stdout
    assert "Deleted habit" in result.stdout
    assert "No habits found" in result.stdout


def test_shell_help_and_exit(cli_env) -> None:
    result = runner.invoke(cli.app, ["shell"], input="help\nexit\n", env=cli_env)

    assert result.exit_code == 0
    assert "habit_tracker_cli" in result.stdout
    assert "Available commands" in result.stdout
    assert "Remove today's completion for a habit." in result.stdout
    assert "Delete a habit and all of its completion history." in result.stdout
    assert "Commands: add, list, today, done, undo, delete, streak, report, clear-data" in result.stdout
    assert "Special: help, man, clear, exit, q" in result.stdout
    assert "Delete the local database" in result.stdout
    assert "self-remove" not in result.stdout


def test_shell_clear_resets_result(cli_env) -> None:
    result = runner.invoke(cli.app, ["shell"], input='add "Read" --daily\nclear\nq\n', env=cli_env)

    assert result.exit_code == 0
    assert "Added habit" in result.stdout
    assert "Last command: clear" in result.stdout


def test_shell_redraws_each_iteration(monkeypatch, app_home) -> None:
    clear_calls: list[bool] = []
    inputs = iter(["help", "q"])

    def fake_clear() -> None:
        clear_calls.append(True)

    def fake_input(prompt: str) -> str:
        assert prompt == "habit> "
        return next(inputs)

    monkeypatch.setattr(cli.console, "clear", fake_clear)
    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setenv("HABIT_TRACKER_HOME", str(app_home))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    cli.run_shell()

    assert len(clear_calls) >= 2


def test_shell_help_for_command(cli_env) -> None:
    result = runner.invoke(cli.app, ["shell"], input="help add\nq\n", env=cli_env)

    assert result.exit_code == 0
    assert "add" in result.stdout
    assert "Create a habit with a daily schedule or specific weekdays." in result.stdout
    assert "add NAME --daily" in result.stdout


def test_shell_manual_for_command(cli_env) -> None:
    result = runner.invoke(cli.app, ["shell"], input="man report\nq\n", env=cli_env)

    assert result.exit_code == 0
    assert "NAME" in result.stdout
    assert "USAGE" in result.stdout
    assert "DESCRIPTION" in result.stdout
    assert "EXAMPLES" in result.stdout
    assert "report --week" in result.stdout


def test_shell_help_for_delete_command(cli_env) -> None:
    result = runner.invoke(cli.app, ["shell"], input="help delete\nq\n", env=cli_env)

    assert result.exit_code == 0
    assert "delete" in result.stdout
    assert "Delete a habit and all of its completion history." in result.stdout
    assert "delete NAME" in result.stdout


@pytest.mark.skipif(not PROMPT_TOOLKIT_TESTS, reason="prompt_toolkit is not installed")
def test_shell_completer_completes_commands() -> None:
    completer = cli.HabitShellCompleter(cli.build_service)
    completions = list(completer.get_completions(Document(text="do", cursor_position=2), None))

    assert any(item.text == "done" for item in completions)


@pytest.mark.skipif(not PROMPT_TOOLKIT_TESTS, reason="prompt_toolkit is not installed")
def test_shell_completer_completes_habit_names(service, monkeypatch) -> None:
    service.add_habit("Morning Walk", daily=True, days_csv=None)
    monkeypatch.setattr(cli, "build_service", lambda: service)
    completer = cli.HabitShellCompleter(cli.build_service)

    completions = list(completer.get_completions(Document(text="done Mo", cursor_position=7), None))

    assert any(item.text == '"Morning Walk"' for item in completions)


@pytest.mark.skipif(not PROMPT_TOOLKIT_TESTS, reason="prompt_toolkit is not installed")
def test_shell_completer_completes_habit_names_for_undo_and_delete(cli_env, monkeypatch) -> None:
    for key, value in cli_env.items():
        monkeypatch.setenv(key, value)

    service = cli.build_service()
    service.add_habit("Morning Walk", daily=True, days_csv=None)
    service.close()

    undo_completions = list(
        cli.HabitShellCompleter(cli.build_service).get_completions(Document(text="undo Mo", cursor_position=7), None)
    )
    delete_completions = list(
        cli.HabitShellCompleter(cli.build_service).get_completions(Document(text="delete Mo", cursor_position=9), None)
    )

    assert any(item.text == '"Morning Walk"' for item in undo_completions)
    assert any(item.text == '"Morning Walk"' for item in delete_completions)


def test_main_without_subcommands_starts_shell(monkeypatch) -> None:
    called = {"shell": False}

    def fake_run_shell() -> None:
        called["shell"] = True

    monkeypatch.setattr(cli, "run_shell", fake_run_shell)
    monkeypatch.setattr(sys, "argv", ["habit-tracker"])

    cli.main()

    assert called["shell"] is True
