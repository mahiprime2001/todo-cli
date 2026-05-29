"""Persistence layer for the to-do list.

On disk the file is a JSON object: ``{"version": 2, "tasks": [ ... ]}``.
For backward compatibility we also read the legacy format, which was a bare
JSON array of task objects (version 1).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import TaskList

SCHEMA_VERSION = 2
DEFAULT_PATH = Path.home() / ".todo-cli" / "tasks.json"


def data_path() -> Path:
    """Return the file where tasks are stored (overridable via TODO_CLI_DATA)."""
    override = os.environ.get("TODO_CLI_DATA")
    return Path(override) if override else DEFAULT_PATH


def _read_raw() -> list[dict]:
    """Read the raw task dicts from disk, handling both schema versions."""
    path = data_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable file: start fresh rather than crash.
        return []

    if isinstance(data, list):
        # Legacy v1 format: a bare array of tasks.
        return data
    if isinstance(data, dict):
        return data.get("tasks", [])
    return []


def load() -> TaskList:
    """Load all tasks into a TaskList."""
    return TaskList.from_dicts(_read_raw())


def save(task_list: TaskList) -> None:
    """Persist a TaskList to disk in the current schema version."""
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": SCHEMA_VERSION, "tasks": task_list.to_dicts()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
