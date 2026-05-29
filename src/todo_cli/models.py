"""Domain model for the to-do list.

`Task` is a single item; `TaskList` owns a collection of tasks plus all the
business logic (adding, filtering, sorting, editing). The CLI and storage
layers stay thin by delegating here.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Iterable, Optional


class Priority(str, Enum):
    """Task priority. Inherits from str so it serializes cleanly to JSON."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        """Sort weight: high sorts before medium before low."""
        return {"high": 0, "medium": 1, "low": 2}[self.value]

    @property
    def marker(self) -> str:
        """Short symbol used in compact listings."""
        return {"high": "!!!", "medium": "!!", "low": "!"}[self.value]


def now_iso() -> str:
    """Current UTC time as an ISO 8601 string (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today() -> date:
    """Today's date in UTC. Wrapped so tests can reason about it."""
    return datetime.now(timezone.utc).date()


_REL_RE = re.compile(r"^\+(\d+)([dwm])$")


def parse_due(value: Optional[str]) -> Optional[str]:
    """Parse a user-supplied due date into an ISO date string (YYYY-MM-DD).

    Accepts:
      - "today", "tomorrow"
      - "+Nd" / "+Nw" / "+Nm"  (N days / weeks / months-as-30-days from today)
      - an explicit ISO date "YYYY-MM-DD"

    Returns None for an empty value. Raises ValueError on anything unparseable.
    """
    if value is None:
        return None
    value = value.strip().lower()
    if not value:
        return None

    if value == "today":
        return today().isoformat()
    if value == "tomorrow":
        return (today() + timedelta(days=1)).isoformat()

    rel = _REL_RE.match(value)
    if rel:
        amount = int(rel.group(1))
        unit = rel.group(2)
        days = {"d": 1, "w": 7, "m": 30}[unit] * amount
        return (today() + timedelta(days=days)).isoformat()

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(
            f"Could not understand due date {value!r}. "
            "Use YYYY-MM-DD, 'today', 'tomorrow', or '+Nd'/'+Nw'/'+Nm'."
        ) from exc


@dataclass
class Task:
    """A single to-do item."""

    id: int
    text: str
    done: bool = False
    priority: Priority = Priority.MEDIUM
    tags: list[str] = field(default_factory=list)
    due: Optional[str] = None  # ISO date string
    notes: str = ""
    created: str = field(default_factory=now_iso)
    completed: Optional[str] = None  # ISO datetime string

    def to_dict(self) -> dict:
        data = asdict(self)
        data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Build a Task from stored JSON, tolerating older/partial records."""
        return cls(
            id=int(data["id"]),
            text=data.get("text", ""),
            done=bool(data.get("done", False)),
            priority=Priority(data.get("priority", "medium")),
            tags=list(data.get("tags", [])),
            due=data.get("due"),
            notes=data.get("notes", ""),
            created=data.get("created", now_iso()),
            completed=data.get("completed"),
        )

    @property
    def due_date(self) -> Optional[date]:
        return date.fromisoformat(self.due) if self.due else None

    @property
    def is_overdue(self) -> bool:
        d = self.due_date
        return bool(d and not self.done and d < today())

    @property
    def is_due_soon(self) -> bool:
        """Due today or within the next 2 days (and not overdue/done)."""
        d = self.due_date
        if not d or self.done:
            return False
        return today() <= d <= today() + timedelta(days=2)


class TaskList:
    """An ordered collection of tasks with all the operations on them."""

    def __init__(self, tasks: Optional[Iterable[Task]] = None) -> None:
        self.tasks: list[Task] = list(tasks) if tasks else []

    # --- (de)serialization -------------------------------------------------
    @classmethod
    def from_dicts(cls, raw: Iterable[dict]) -> "TaskList":
        return cls(Task.from_dict(d) for d in raw)

    def to_dicts(self) -> list[dict]:
        return [t.to_dict() for t in self.tasks]

    # --- lookups -----------------------------------------------------------
    def get(self, task_id: int) -> Optional[Task]:
        return next((t for t in self.tasks if t.id == task_id), None)

    def next_id(self) -> int:
        return max((t.id for t in self.tasks), default=0) + 1

    def all_tags(self) -> dict[str, int]:
        """Map every tag to the number of tasks using it."""
        counts: dict[str, int] = {}
        for t in self.tasks:
            for tag in t.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return dict(sorted(counts.items()))

    # --- mutations ---------------------------------------------------------
    def add(
        self,
        text: str,
        *,
        priority: Priority = Priority.MEDIUM,
        tags: Optional[list[str]] = None,
        due: Optional[str] = None,
        notes: str = "",
    ) -> Task:
        task = Task(
            id=self.next_id(),
            text=text,
            priority=priority,
            tags=sorted(set(tags or [])),
            due=parse_due(due),
            notes=notes,
        )
        self.tasks.append(task)
        return task

    def complete(self, task_id: int) -> Optional[Task]:
        task = self.get(task_id)
        if task and not task.done:
            task.done = True
            task.completed = now_iso()
        return task

    def reopen(self, task_id: int) -> Optional[Task]:
        task = self.get(task_id)
        if task and task.done:
            task.done = False
            task.completed = None
        return task

    def remove(self, task_id: int) -> bool:
        task = self.get(task_id)
        if task is None:
            return False
        self.tasks.remove(task)
        return True

    def clear(self, *, done_only: bool = False) -> int:
        """Remove tasks; returns how many were removed."""
        before = len(self.tasks)
        if done_only:
            self.tasks = [t for t in self.tasks if not t.done]
        else:
            self.tasks = []
        return before - len(self.tasks)

    # --- querying ----------------------------------------------------------
    def filter(
        self,
        *,
        include_done: bool = False,
        priority: Optional[Priority] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        overdue: bool = False,
    ) -> list[Task]:
        result = list(self.tasks)
        if not include_done:
            result = [t for t in result if not t.done]
        if priority is not None:
            result = [t for t in result if t.priority == priority]
        if tag is not None:
            result = [t for t in result if tag in t.tags]
        if search:
            needle = search.lower()
            result = [
                t for t in result
                if needle in t.text.lower() or needle in t.notes.lower()
            ]
        if overdue:
            result = [t for t in result if t.is_overdue]
        return result

    @staticmethod
    def sort(tasks: list[Task], by: str = "id") -> list[Task]:
        """Return a sorted copy of `tasks`. `by` is one of id/priority/due/created."""
        if by == "priority":
            key = lambda t: (t.priority.rank, t.id)  # noqa: E731
        elif by == "due":
            # Tasks without a due date sort last.
            key = lambda t: (t.due or "9999-12-31", t.id)  # noqa: E731
        elif by == "created":
            key = lambda t: t.created  # noqa: E731
        else:  # "id"
            key = lambda t: t.id  # noqa: E731
        return sorted(tasks, key=key)

    def stats(self) -> dict:
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t.done)
        pending = total - done
        overdue = sum(1 for t in self.tasks if t.is_overdue)
        by_priority = {
            p.value: sum(1 for t in self.tasks if t.priority == p and not t.done)
            for p in Priority
        }
        return {
            "total": total,
            "done": done,
            "pending": pending,
            "overdue": overdue,
            "by_priority": by_priority,
        }
