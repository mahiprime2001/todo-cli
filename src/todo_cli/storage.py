"""Persistence layer for the to-do list.

Tasks are stored as a JSON array in a single file. Each task is a dict with
keys: id (int), text (str), done (bool), created (ISO 8601 str).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Allow overriding the data location (used by tests and power users).
DEFAULT_PATH = Path.home() / ".todo-cli" / "tasks.json"


def data_path() -> Path:
    """Return the file where tasks are stored."""
    override = os.environ.get("TODO_CLI_DATA")
    return Path(override) if override else DEFAULT_PATH


def load_tasks() -> list[dict]:
    """Read all tasks from disk, returning an empty list if none exist."""
    path = data_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable file: start fresh rather than crash.
        return []


def save_tasks(tasks: list[dict]) -> None:
    """Write all tasks to disk, creating the directory if needed."""
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


def next_id(tasks: list[dict]) -> int:
    """Return the next free task id (max existing id + 1)."""
    return max((t["id"] for t in tasks), default=0) + 1


def now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
