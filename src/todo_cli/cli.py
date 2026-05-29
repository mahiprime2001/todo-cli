"""Command-line interface for todo-cli, built with Typer + Rich."""

from __future__ import annotations

import csv
import io
import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import storage
from .models import Priority, Task, TaskList, parse_due

# On legacy Windows consoles the default code page (e.g. cp1252) cannot encode
# many characters, which would crash on any Unicode the user types. Prefer
# UTF-8 where the stream supports reconfiguring.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

app = typer.Typer(
    help="A friendly, full-featured command-line to-do manager.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


# --- helpers ---------------------------------------------------------------
def _priority_style(priority: Priority) -> str:
    return {"high": "bold red", "medium": "yellow", "low": "dim"}[priority.value]


def _due_render(task: Task) -> str:
    if not task.due:
        return ""
    if task.is_overdue:
        return f"[bold red]{task.due} (overdue)[/bold red]"
    if task.is_due_soon:
        return f"[yellow]{task.due}[/yellow]"
    return task.due


def _abort(message: str) -> None:
    err_console.print(f"[red]{message}[/red]")
    raise typer.Exit(code=1)


# --- commands --------------------------------------------------------------
@app.command()
def add(
    text: str = typer.Argument(..., help="What you need to do."),
    priority: Priority = typer.Option(
        Priority.MEDIUM, "--priority", "-p", help="Task priority."
    ),
    tag: list[str] = typer.Option(
        None, "--tag", "-t", help="Tag(s) for the task (repeatable)."
    ),
    due: Optional[str] = typer.Option(
        None, "--due", "-d",
        help="Due date: YYYY-MM-DD, 'today', 'tomorrow', or '+Nd'/'+Nw'/'+Nm'.",
    ),
    note: str = typer.Option("", "--note", "-n", help="A longer note."),
) -> None:
    """Add a new task."""
    tasks = storage.load()
    try:
        task = tasks.add(
            text, priority=priority, tags=tag or [], due=due, notes=note
        )
    except ValueError as exc:
        _abort(str(exc))
    storage.save(tasks)
    console.print(f"[green]Added[/green] task #{task.id}: {text}")


@app.command(name="list")
def list_tasks(
    all_: bool = typer.Option(False, "--all", "-a", help="Include completed tasks."),
    priority: Optional[Priority] = typer.Option(
        None, "--priority", "-p", help="Only this priority."
    ),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Only this tag."),
    search: Optional[str] = typer.Option(
        None, "--search", "-s", help="Match text or notes."
    ),
    overdue: bool = typer.Option(False, "--overdue", help="Only overdue tasks."),
    sort: str = typer.Option(
        "id", "--sort", help="Sort by: id, priority, due, created."
    ),
) -> None:
    """List tasks (pending only by default), with filtering and sorting."""
    tasks = storage.load()
    matched = tasks.filter(
        include_done=all_,
        priority=priority,
        tag=tag,
        search=search,
        overdue=overdue,
    )
    matched = TaskList.sort(matched, by=sort)

    if not matched:
        console.print("[dim]No matching tasks.[/dim]")
        return

    table = Table(title="To-Do")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("St", justify="center")
    table.add_column("Pri", justify="center")
    table.add_column("Task")
    table.add_column("Due")
    table.add_column("Tags", style="magenta")
    for t in matched:
        check = "[green]x[/green]" if t.done else " "
        text = f"[strike dim]{t.text}[/strike dim]" if t.done else t.text
        pri = f"[{_priority_style(t.priority)}]{t.priority.value}[/]"
        table.add_row(
            str(t.id), check, pri, text, _due_render(t), ", ".join(t.tags)
        )
    console.print(table)


@app.command()
def show(task_id: int = typer.Argument(..., help="ID of the task to inspect.")) -> None:
    """Show the full detail of a single task."""
    task = storage.load().get(task_id)
    if task is None:
        _abort(f"No task with id {task_id}.")

    table = Table(show_header=False, title=f"Task #{task.id}")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Text", task.text)
    table.add_row("Status", "done" if task.done else "pending")
    table.add_row("Priority", task.priority.value)
    table.add_row("Due", task.due or "—")
    table.add_row("Tags", ", ".join(task.tags) or "—")
    table.add_row("Created", task.created)
    table.add_row("Completed", task.completed or "—")
    table.add_row("Notes", task.notes or "—")
    console.print(table)


@app.command()
def done(
    task_ids: list[int] = typer.Argument(..., help="ID(s) of task(s) to complete."),
) -> None:
    """Mark one or more tasks as completed."""
    tasks = storage.load()
    missing = []
    for task_id in task_ids:
        task = tasks.complete(task_id)
        if task is None:
            missing.append(task_id)
        else:
            console.print(f"[green]Completed[/green] task #{task_id}: {task.text}")
    storage.save(tasks)
    if missing:
        _abort(f"No task(s) with id: {', '.join(map(str, missing))}.")


@app.command()
def undone(task_id: int = typer.Argument(..., help="ID of the task to reopen.")) -> None:
    """Reopen a completed task (mark it pending again)."""
    tasks = storage.load()
    if tasks.get(task_id) is None:
        _abort(f"No task with id {task_id}.")
    tasks.reopen(task_id)
    storage.save(tasks)
    console.print(f"[green]Reopened[/green] task #{task_id}.")


@app.command()
def edit(
    task_id: int = typer.Argument(..., help="ID of the task to edit."),
    text: Optional[str] = typer.Option(None, "--text", help="New task text."),
    priority: Optional[Priority] = typer.Option(
        None, "--priority", "-p", help="New priority."
    ),
    due: Optional[str] = typer.Option(
        None, "--due", "-d", help="New due date (use 'none' to clear)."
    ),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="New note text."),
    add_tag: list[str] = typer.Option(None, "--add-tag", help="Tag(s) to add."),
    remove_tag: list[str] = typer.Option(
        None, "--remove-tag", help="Tag(s) to remove."
    ),
) -> None:
    """Edit fields of an existing task."""
    tasks = storage.load()
    task = tasks.get(task_id)
    if task is None:
        _abort(f"No task with id {task_id}.")

    if text is not None:
        task.text = text
    if priority is not None:
        task.priority = priority
    if note is not None:
        task.notes = note
    if due is not None:
        if due.strip().lower() == "none":
            task.due = None
        else:
            try:
                task.due = parse_due(due)
            except ValueError as exc:
                _abort(str(exc))
    if add_tag:
        task.tags = sorted(set(task.tags) | set(add_tag))
    if remove_tag:
        task.tags = sorted(set(task.tags) - set(remove_tag))

    storage.save(tasks)
    console.print(f"[green]Updated[/green] task #{task_id}.")


@app.command()
def remove(
    task_ids: list[int] = typer.Argument(..., help="ID(s) of task(s) to delete."),
) -> None:
    """Delete one or more tasks."""
    tasks = storage.load()
    missing = [tid for tid in task_ids if not tasks.remove(tid)]
    storage.save(tasks)
    removed = [tid for tid in task_ids if tid not in missing]
    if removed:
        console.print(f"[green]Removed[/green] task(s): {', '.join(map(str, removed))}.")
    if missing:
        _abort(f"No task(s) with id: {', '.join(map(str, missing))}.")


@app.command()
def clear(
    done_only: bool = typer.Option(
        False, "--done", help="Only clear completed tasks."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
) -> None:
    """Delete completed tasks (--done) or every task."""
    tasks = storage.load()
    target = "completed tasks" if done_only else "ALL tasks"
    if not force:
        typer.confirm(f"Delete {target}?", abort=True)
    count = tasks.clear(done_only=done_only)
    storage.save(tasks)
    console.print(f"[green]Removed {count} task(s).[/green]")


@app.command()
def tags() -> None:
    """List all tags and how many tasks use each."""
    counts = storage.load().all_tags()
    if not counts:
        console.print("[dim]No tags yet.[/dim]")
        return
    table = Table(title="Tags")
    table.add_column("Tag", style="magenta")
    table.add_column("Count", justify="right", style="cyan")
    for name, count in counts.items():
        table.add_row(name, str(count))
    console.print(table)


@app.command()
def stats() -> None:
    """Show a summary of your tasks."""
    s = storage.load().stats()
    table = Table(title="Stats", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Total", str(s["total"]))
    table.add_row("Pending", str(s["pending"]))
    table.add_row("Done", str(s["done"]))
    table.add_row("Overdue", f"[red]{s['overdue']}[/red]" if s["overdue"] else "0")
    table.add_section()
    for name, count in s["by_priority"].items():
        table.add_row(f"Pending - {name}", str(count))
    console.print(table)


@app.command()
def export(
    fmt: str = typer.Option("json", "--format", "-f", help="json, csv, or md."),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write to a file instead of stdout."
    ),
) -> None:
    """Export all tasks as JSON, CSV, or Markdown."""
    tasks = storage.load()
    fmt = fmt.lower()

    if fmt == "json":
        rendered = json.dumps(tasks.to_dicts(), indent=2)
    elif fmt == "csv":
        buf = io.StringIO()
        fields = ["id", "text", "done", "priority", "tags", "due", "notes", "created", "completed"]
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        for t in tasks.tasks:
            row = t.to_dict()
            row["tags"] = ";".join(row["tags"])
            writer.writerow(row)
        rendered = buf.getvalue()
    elif fmt in ("md", "markdown"):
        lines = ["# To-Do", ""]
        for t in tasks.tasks:
            box = "x" if t.done else " "
            extra = []
            if t.due:
                extra.append(f"due {t.due}")
            if t.tags:
                extra.append(" ".join(f"#{tag}" for tag in t.tags))
            suffix = f"  ({', '.join(extra)})" if extra else ""
            lines.append(f"- [{box}] **{t.priority.value}** {t.text}{suffix}")
        rendered = "\n".join(lines) + "\n"
    else:
        _abort(f"Unknown format {fmt!r}. Use json, csv, or md.")

    if output:
        from pathlib import Path

        Path(output).write_text(rendered, encoding="utf-8")
        console.print(f"[green]Exported to {output}.[/green]")
    else:
        # Plain print so output is pipeable/redirectable without Rich markup.
        print(rendered)


if __name__ == "__main__":
    app()
