"""Command-line interface for todo-cli, built with Typer + Rich."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from . import storage

app = typer.Typer(
    help="A simple, friendly command-line to-do manager.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def add(text: str = typer.Argument(..., help="What you need to do.")) -> None:
    """Add a new task."""
    tasks = storage.load_tasks()
    task = {
        "id": storage.next_id(tasks),
        "text": text,
        "done": False,
        "created": storage.now_iso(),
    }
    tasks.append(task)
    storage.save_tasks(tasks)
    console.print(f"[green]Added[/green] task #{task['id']}: {text}")


@app.command(name="list")
def list_tasks(
    all_: bool = typer.Option(
        False, "--all", "-a", help="Include completed tasks."
    ),
) -> None:
    """List your tasks (pending only by default)."""
    tasks = storage.load_tasks()
    if not all_:
        tasks = [t for t in tasks if not t["done"]]

    if not tasks:
        console.print("[dim]No tasks. Enjoy your day![/dim]")
        raise typer.Exit()

    table = Table(title="To-Do")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Task")
    for t in tasks:
        status = "[green]done[/green]" if t["done"] else "[yellow]pending[/yellow]"
        text = f"[strike]{t['text']}[/strike]" if t["done"] else t["text"]
        table.add_row(str(t["id"]), status, text)
    console.print(table)


@app.command()
def done(task_id: int = typer.Argument(..., help="ID of the task to complete.")) -> None:
    """Mark a task as completed."""
    tasks = storage.load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            if t["done"]:
                console.print(f"[dim]Task #{task_id} is already done.[/dim]")
                return
            t["done"] = True
            storage.save_tasks(tasks)
            console.print(f"[green]Completed[/green] task #{task_id}: {t['text']}")
            return
    console.print(f"[red]No task with id {task_id}.[/red]")
    raise typer.Exit(code=1)


@app.command()
def remove(task_id: int = typer.Argument(..., help="ID of the task to delete.")) -> None:
    """Delete a task."""
    tasks = storage.load_tasks()
    remaining = [t for t in tasks if t["id"] != task_id]
    if len(remaining) == len(tasks):
        console.print(f"[red]No task with id {task_id}.[/red]")
        raise typer.Exit(code=1)
    storage.save_tasks(remaining)
    console.print(f"[green]Removed[/green] task #{task_id}.")


@app.command()
def clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
) -> None:
    """Delete all tasks."""
    if not force:
        typer.confirm("Delete ALL tasks?", abort=True)
    storage.save_tasks([])
    console.print("[green]All tasks cleared.[/green]")


if __name__ == "__main__":
    app()
