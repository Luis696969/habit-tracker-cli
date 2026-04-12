from __future__ import annotations

import json
import shlex
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from typing import Callable

import click
import typer
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from habit_tracker_cli.db import get_connection
from habit_tracker_cli.maintenance import clear_data_paths, describe_data_paths
from habit_tracker_cli.paths import AppPaths, ensure_parent_directories, resolve_app_paths
from habit_tracker_cli.render import (
    render_habit_list,
    render_path_statuses,
    render_streak,
    render_today,
    render_weekly_report,
    schedule_label,
)
from habit_tracker_cli.repository import HabitRepository
from habit_tracker_cli.services import HabitNotFoundError, HabitService, HabitValidationError

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import FileHistory

    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency is installed in normal use.
    PromptSession = None  # type: ignore[assignment]
    FileHistory = None  # type: ignore[assignment]
    PROMPT_TOOLKIT_AVAILABLE = False

    class Completer:  # type: ignore[no-redef]
        pass

    class Completion:  # type: ignore[no-redef]
        pass

app = typer.Typer(help="Track habits from the terminal.")
console = Console()
error_console = Console(stderr=True)
SHELL_EXIT_COMMANDS = {"exit", "q"}
SHELL_TITLE = "habit_tracker_cli"
SHELL_COMMAND_NAMES = (
    "add",
    "list",
    "today",
    "done",
    "streak",
    "report",
    "help",
    "man",
    "clear",
    "clear-data",
    "exit",
    "q",
)


@dataclass(frozen=True, slots=True)
class CommandDoc:
    short: str
    usage: tuple[str, ...]
    description: str
    options: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


COMMAND_DOCS: dict[str, CommandDoc] = {
    "add": CommandDoc(
        short="Create a habit with a daily schedule or specific weekdays.",
        usage=("add NAME --daily", "add NAME --days mon,wed,fri"),
        description=(
            "Adds a new habit to the database. Habit names are trim-safe and matched case-insensitively."
        ),
        options=(
            "--daily    Create a daily habit.",
            "--days     Comma-separated weekdays using mon,tue,wed,thu,fri,sat,sun.",
        ),
        examples=('add "Read 20 min" --daily', 'add "Go to the gym" --days mon,wed,fri'),
        notes=(
            "--daily and --days are mutually exclusive.",
            "Duplicate names are rejected using a normalized name.",
        ),
    ),
    "list": CommandDoc(
        short="Show all active habits and their schedules.",
        usage=("list",),
        description="Displays all stored habits in a table with their schedule and creation date.",
        examples=("list",),
    ),
    "today": CommandDoc(
        short="Show habits scheduled for today and their current status.",
        usage=("today",),
        description="Lists only the habits due on the current local date and marks each as done or pending.",
        examples=("today",),
    ),
    "done": CommandDoc(
        short="Mark a habit as completed for today.",
        usage=("done NAME",),
        description="Marks the named habit as completed for the current local date.",
        examples=('done "Read 20 min"',),
        notes=(
            "The operation is idempotent.",
            "Names are matched case-insensitively and ignore surrounding spaces.",
        ),
    ),
    "streak": CommandDoc(
        short="Show the current streak for a habit.",
        usage=("streak NAME",),
        description="Calculates the current streak up to the most recent scheduled date that is not in the future.",
        examples=('streak "Read 20 min"',),
    ),
    "report": CommandDoc(
        short="Show the weekly report for the current week.",
        usage=("report", "report --week"),
        description="Displays a Monday-to-Sunday summary of scheduled, completed, and missed habit occurrences.",
        options=("--week     Explicitly request the weekly report.",),
        examples=("report", "report --week"),
        notes=("In v1, report and report --week are equivalent.",),
    ),
    "clear": CommandDoc(
        short="Clear the current result panel.",
        usage=("clear",),
        description="Removes the last shell output while keeping the shell header visible.",
        examples=("clear",),
    ),
    "clear-data": CommandDoc(
        short="Delete the local database, history, and app state without uninstalling the app.",
        usage=("clear-data", "clear-data --yes"),
        description=(
            "Deletes the SQLite database, shell history, and app-managed data/state/config/cache paths."
        ),
        options=("--yes      Skip the confirmation prompt.",),
        examples=("clear-data", "clear-data --yes"),
        notes=(
            "Missing files are ignored safely.",
            "If you run this inside an active shell, history/state files may be recreated until the session exits.",
        ),
    ),
    "help": CommandDoc(
        short="Show general shell help or a short help entry for one command.",
        usage=("help", "help COMMAND"),
        description="Shows the list of available commands or a short command-specific summary inside the shell view.",
        examples=("help", "help add"),
    ),
    "man": CommandDoc(
        short="Show the manual index or a full manual page for one command.",
        usage=("man", "man COMMAND"),
        description="Displays a command index or a richer manual page with usage, examples, and notes.",
        examples=("man", "man add"),
    ),
    "exit": CommandDoc(
        short="Exit the interactive shell.",
        usage=("exit",),
        description="Closes the shell and returns control to the current terminal session.",
        examples=("exit",),
    ),
    "q": CommandDoc(
        short="Exit the interactive shell.",
        usage=("q",),
        description="Short alias for exiting the shell.",
        examples=("q",),
    ),
}


def build_service() -> HabitService:
    connection = get_connection()
    repository = HabitRepository(connection)
    return HabitService(repository)


def abort_with_error(message: str) -> None:
    error_console.print(f"[bold red]Error:[/bold red] {message}")
    raise typer.Exit(code=1)


def shell_help_text() -> RenderableType:
    body = Text()
    body.append("Available commands:\n", style="bold")
    for name in ("add", "list", "today", "done", "streak", "report", "clear-data"):
        body.append(f"  {name:<12}", style="cyan")
        body.append(f"{COMMAND_DOCS[name].short}\n")
    body.append("\nSpecial commands:\n", style="bold")
    for name in ("help", "man", "clear", "exit", "q"):
        body.append(f"  {name:<12}", style="magenta")
        body.append(f"{COMMAND_DOCS[name].short}\n")
    return body


def render_command_help(command_name: str) -> RenderableType:
    command = command_name.lower()
    doc = COMMAND_DOCS.get(command)
    if doc is None:
        return f"Error: Unknown command '{command_name}'. Use `help` to see the available commands."

    body = Text()
    body.append(f"{command}\n", style="bold cyan")
    body.append(f"{doc.short}\n\n")
    body.append("Usage:\n", style="bold")
    for usage in doc.usage:
        body.append(f"  {usage}\n")
    return body


def render_manual_index() -> RenderableType:
    body = Text()
    body.append("Manual index:\n", style="bold")
    for name in ("add", "list", "today", "done", "streak", "report", "clear-data", "help", "man", "clear", "exit", "q"):
        body.append(f"  {name:<12}", style="cyan")
        body.append(f"{COMMAND_DOCS[name].short}\n")
    return body


def render_manual_page(command_name: str) -> RenderableType:
    command = command_name.lower()
    doc = COMMAND_DOCS.get(command)
    if doc is None:
        return f"Error: Unknown command '{command_name}'. Use `man` to see the command index."

    body = Text()
    body.append("NAME\n", style="bold")
    body.append(f"  {command} - {doc.short}\n\n")
    body.append("USAGE\n", style="bold")
    for usage in doc.usage:
        body.append(f"  {usage}\n")
    body.append("\nDESCRIPTION\n", style="bold")
    body.append(f"  {doc.description}\n")

    if doc.options:
        body.append("\nOPTIONS\n", style="bold")
        for option in doc.options:
            body.append(f"  {option}\n")

    if doc.examples:
        body.append("\nEXAMPLES\n", style="bold")
        for example in doc.examples:
            body.append(f"  {example}\n")

    if doc.notes:
        body.append("\nNOTES\n", style="bold")
        for note in doc.notes:
            body.append(f"  {note}\n")

    return body


def render_shell_header(status: str | None = None) -> Panel:
    body = Text()
    body.append(f"{SHELL_TITLE}\n", style="bold cyan")
    body.append("Commands: add, list, today, done, streak, report, clear-data\n")
    body.append("Special: help, man, clear, exit, q")
    if status:
        body.append(f"\nStatus: {status}", style="green")
    return Panel(body, title="Interactive Shell", border_style="cyan")


def render_shell_view(last_output: RenderableType | None, status: str | None = None) -> Group:
    has_output = last_output is not None and (not isinstance(last_output, str) or bool(last_output.strip()))
    if has_output and last_output is not None:
        output_panel = Panel(last_output, title="Result", border_style="green")
    else:
        output_panel = Panel("No output yet. Type `help`, `man`, or run a command.", title="Result", border_style="dim")
    return Group(render_shell_header(status=status), output_panel)


@contextmanager
def command_capture() -> tuple[StringIO, StringIO]:
    global console, error_console

    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    original_console = console
    original_error_console = error_console
    console = Console(file=stdout_buffer, force_terminal=False, color_system=None)
    error_console = Console(file=stderr_buffer, force_terminal=False, color_system=None)
    try:
        yield stdout_buffer, stderr_buffer
    finally:
        console = original_console
        error_console = original_error_console


def dispatch_command(tokens: list[str]) -> str:
    try:
        with command_capture() as (stdout_buffer, stderr_buffer):
            app(args=tokens, prog_name="habit-tracker", standalone_mode=False)
    except click.ClickException as exc:
        return exc.format_message()
    except click.exceptions.Exit:
        return ""

    stdout_text = stdout_buffer.getvalue().strip()
    stderr_text = stderr_buffer.getvalue().strip()
    parts = [part for part in (stdout_text, stderr_text) if part]
    return "\n".join(parts)


class HabitShellCompleter(Completer):
    def __init__(self, service_factory: Callable[[], HabitService]) -> None:
        self.service_factory = service_factory

    def get_completions(self, document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor
        current_word = document.get_word_before_cursor(WORD=True)
        try:
            tokens = shlex.split(text)
            new_token = not text or text[-1].isspace()
        except ValueError:
            tokens = text.split()
            new_token = not text or text[-1].isspace()

        if not tokens:
            yield from self._complete_command(current_word)
            return

        if len(tokens) == 1 and not new_token:
            yield from self._complete_command(current_word)
            return

        command = tokens[0].lower()
        prefix = "" if new_token else current_word
        if command in {"done", "streak"}:
            yield from self._complete_habit_names(prefix)
            return
        if command in {"help", "man"}:
            yield from self._complete_command(prefix)
            return

    def _complete_command(self, prefix: str):
        for name in SHELL_COMMAND_NAMES:
            if name.startswith(prefix):
                yield Completion(name, start_position=-len(prefix))

    def _complete_habit_names(self, prefix: str):
        service = self.service_factory()
        try:
            for name in service.list_habit_names():
                candidate = _quote_completion(name)
                if candidate.lower().startswith(prefix.lower()):
                    yield Completion(candidate, start_position=-len(prefix))
        finally:
            service.close()


def _quote_completion(value: str) -> str:
    if " " in value:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _save_shell_state(app_paths: AppPaths, status: str, last_command: str | None) -> None:
    ensure_parent_directories(app_paths)
    payload = {"status": status, "last_command": last_command}
    app_paths.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_prompt_session(app_paths: AppPaths):
    if not PROMPT_TOOLKIT_AVAILABLE or not sys.stdin.isatty() or not sys.stdout.isatty():
        return None
    ensure_parent_directories(app_paths)
    return PromptSession(
        history=FileHistory(str(app_paths.history_path)),
        completer=HabitShellCompleter(build_service),
        complete_while_typing=False,
    )


def _prompt_input(prompt_text: str, session=None) -> str:
    if session is None:
        return input(prompt_text)
    return session.prompt(prompt_text)


def _confirm_action(prompt_text: str, *, session=None) -> bool:
    if session is None:
        return typer.confirm(prompt_text, default=False)
    response = session.prompt(f"{prompt_text} [y/N]: ")
    return response.strip().lower() in {"y", "yes"}


def _show_preview(renderable: RenderableType, *, session=None) -> None:
    if session is None:
        console.print(renderable)
        return
    console.clear()
    console.print(render_shell_view(last_output=renderable, status="Pending confirmation"))


def _run_clear_data_flow(*, assume_yes: bool, session=None) -> RenderableType:
    statuses = describe_data_paths()
    preview = render_path_statuses("App Data Paths", statuses)
    if not assume_yes:
        _show_preview(preview, session=session)
    confirmed = assume_yes or _confirm_action("Delete all habit_tracker_cli data?", session=session)
    summary_title = "Clear Data"
    if confirmed:
        deleted_paths = clear_data_paths()
        message = (
            f"Deleted {len(deleted_paths)} path(s)." if deleted_paths else "No app data was found to delete."
        )
    else:
        message = "Clear-data cancelled."
    return Group(preview, Panel(message, title=summary_title))


@app.command()
def add(
    name: str = typer.Argument(..., metavar="NAME", help="Habit name. Wrap in quotes when it contains spaces."),
    daily: bool = typer.Option(False, "--daily", help="Create a daily habit."),
    days: str | None = typer.Option(None, "--days", help="Comma-separated weekdays such as mon,wed,fri."),
) -> None:
    service = build_service()
    try:
        habit = service.add_habit(name, daily=daily, days_csv=days)
    except HabitValidationError as exc:
        abort_with_error(str(exc))
    finally:
        service.close()

    console.print(f"Added habit '[cyan]{habit.name}[/cyan]' with schedule [magenta]{schedule_label(habit)}[/magenta].")


@app.command(name="list")
def list_habits() -> None:
    service = build_service()
    try:
        habits = service.list_habits()
    finally:
        service.close()

    if not habits:
        console.print("No habits found. Add one with `habit-tracker add`.")
        return

    console.print(render_habit_list(habits))


@app.command()
def today() -> None:
    service = build_service()
    try:
        habits = service.get_today_habits()
    finally:
        service.close()

    if not habits:
        console.print("No habits are scheduled for today.")
        return

    console.print(render_today(habits))


@app.command()
def done(name: str = typer.Argument(..., metavar="NAME", help="Habit name to mark as completed today.")) -> None:
    service = build_service()
    try:
        habit, inserted = service.mark_done(name)
    except HabitValidationError as exc:
        abort_with_error(str(exc))
    except HabitNotFoundError as exc:
        abort_with_error(str(exc))
    finally:
        service.close()

    if inserted:
        console.print(f"Marked '[cyan]{habit.name}[/cyan]' as done for today.")
    else:
        console.print(f"'{habit.name}' was already marked as done for today.")


@app.command()
def streak(name: str = typer.Argument(..., metavar="NAME", help="Habit name to inspect.")) -> None:
    service = build_service()
    try:
        habit, current_streak = service.get_streak(name)
    except HabitValidationError as exc:
        abort_with_error(str(exc))
    except HabitNotFoundError as exc:
        abort_with_error(str(exc))
    finally:
        service.close()

    console.print(render_streak(habit, current_streak))


@app.command()
def report(
    week: bool = typer.Option(False, "--week", help="Show the current weekly report."),
) -> None:
    _ = week
    service = build_service()
    try:
        weekly_report = service.get_weekly_report()
    finally:
        service.close()

    if not weekly_report.rows:
        console.print("No habits found. Add one with `habit-tracker add`.")
        return

    console.print(render_weekly_report(weekly_report))


@app.command(name="clear-data")
def clear_data(
    yes: bool = typer.Option(False, "--yes", help="Delete data without asking for confirmation."),
) -> None:
    console.print(_run_clear_data_flow(assume_yes=yes))


def _handle_shell_command(tokens: list[str], session=None) -> tuple[RenderableType | None, bool]:
    command = tokens[0].lower()

    if command in SHELL_EXIT_COMMANDS:
        return None, True
    if command == "help":
        return (shell_help_text() if len(tokens) == 1 else render_command_help(tokens[1])), False
    if command == "man":
        return (render_manual_index() if len(tokens) == 1 else render_manual_page(tokens[1])), False
    if command == "clear":
        return "", False
    if command == "clear-data":
        return _run_clear_data_flow(assume_yes="--yes" in tokens, session=session), False

    return dispatch_command(tokens), False


@app.command()
def shell() -> None:
    run_shell()


def run_shell() -> None:
    app_paths = resolve_app_paths()
    ensure_parent_directories(app_paths)
    session = _build_prompt_session(app_paths)
    last_output: RenderableType | None = shell_help_text()
    status = "Ready"
    last_command: str | None = None
    _save_shell_state(app_paths, status=status, last_command=last_command)

    while True:
        console.clear()
        console.print(render_shell_view(last_output=last_output, status=status))
        try:
            raw_line = _prompt_input("habit> ", session=session)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        line = raw_line.strip()
        if not line:
            status = "Waiting for command"
            _save_shell_state(app_paths, status=status, last_command=last_command)
            continue

        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            last_output = f"Error: {exc}"
            status = "Parse error"
            _save_shell_state(app_paths, status=status, last_command=last_command)
            continue

        last_command = line
        last_output, should_exit = _handle_shell_command(tokens, session=session)
        status = f"Last command: {line}"
        _save_shell_state(app_paths, status=status, last_command=last_command)
        if should_exit:
            break


def main() -> None:
    if len(sys.argv) <= 1:
        run_shell()
        return
    app()


if __name__ == "__main__":
    main()
