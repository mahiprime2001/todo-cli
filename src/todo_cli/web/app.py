"""FastAPI application exposing the to-do list over HTTP.

The endpoints are a thin shell over the same ``TaskList``/``storage`` layer the
CLI uses, so both interfaces behave identically. A small static frontend
(``static/index.html`` and friends) is served at the root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import storage
from ..models import Priority, Task, TaskList, parse_due

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="todo-cli", description="A friendly to-do manager.")


# --- request/response schemas ---------------------------------------------
class TaskCreate(BaseModel):
    text: str = Field(..., min_length=1)
    priority: Priority = Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    due: Optional[str] = None
    notes: str = ""


class TaskUpdate(BaseModel):
    text: Optional[str] = None
    priority: Optional[Priority] = None
    tags: Optional[list[str]] = None
    due: Optional[str] = None  # "" or null clears it
    notes: Optional[str] = None
    done: Optional[bool] = None


def _task_json(task: Task) -> dict:
    """Serialize a task plus a couple of derived display flags."""
    data = task.to_dict()
    data["is_overdue"] = task.is_overdue
    data["is_due_soon"] = task.is_due_soon
    return data


# --- API -------------------------------------------------------------------
@app.get("/api/tasks")
def list_tasks(
    all: bool = False,
    priority: Optional[Priority] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    overdue: bool = False,
    sort: str = "id",
) -> list[dict]:
    tasks = storage.load()
    matched = tasks.filter(
        include_done=all,
        priority=priority,
        tag=tag,
        search=search,
        overdue=overdue,
    )
    matched = TaskList.sort(matched, by=sort)
    return [_task_json(t) for t in matched]


@app.post("/api/tasks", status_code=201)
def create_task(payload: TaskCreate) -> dict:
    tasks = storage.load()
    try:
        task = tasks.add(
            payload.text,
            priority=payload.priority,
            tags=payload.tags,
            due=payload.due,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    storage.save(tasks)
    return _task_json(task)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    task = storage.load().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"No task with id {task_id}.")
    return _task_json(task)


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate) -> dict:
    tasks = storage.load()
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"No task with id {task_id}.")

    if payload.text is not None:
        task.text = payload.text
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.notes is not None:
        task.notes = payload.notes
    if payload.tags is not None:
        task.tags = sorted(set(payload.tags))
    if payload.due is not None:
        if payload.due == "":
            task.due = None
        else:
            try:
                task.due = parse_due(payload.due)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.done is not None:
        if payload.done:
            tasks.complete(task_id)
        else:
            tasks.reopen(task_id)

    storage.save(tasks)
    return _task_json(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    tasks = storage.load()
    if not tasks.remove(task_id):
        raise HTTPException(status_code=404, detail=f"No task with id {task_id}.")
    storage.save(tasks)


@app.get("/api/tags")
def get_tags() -> dict[str, int]:
    return storage.load().all_tags()


@app.get("/api/stats")
def get_stats() -> dict:
    return storage.load().stats()


# --- frontend --------------------------------------------------------------
@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Launch the web server (used by the ``todo-web`` entry point)."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
