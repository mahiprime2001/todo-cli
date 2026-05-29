"""Unit tests for the domain model (Task, TaskList, date parsing)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from todo_cli.models import Priority, Task, TaskList, parse_due, today


# --- parse_due -------------------------------------------------------------
def test_parse_due_keywords():
    assert parse_due("today") == today().isoformat()
    assert parse_due("tomorrow") == (today() + timedelta(days=1)).isoformat()


def test_parse_due_relative():
    assert parse_due("+3d") == (today() + timedelta(days=3)).isoformat()
    assert parse_due("+2w") == (today() + timedelta(days=14)).isoformat()
    assert parse_due("+1m") == (today() + timedelta(days=30)).isoformat()


def test_parse_due_iso_and_empty():
    assert parse_due("2030-01-15") == "2030-01-15"
    assert parse_due(None) is None
    assert parse_due("") is None


def test_parse_due_invalid_raises():
    with pytest.raises(ValueError):
        parse_due("next thursday")


# --- Task ------------------------------------------------------------------
def test_task_roundtrip_dict():
    t = Task(id=1, text="x", priority=Priority.HIGH, tags=["a"], due="2030-01-01")
    restored = Task.from_dict(t.to_dict())
    assert restored == t


def test_task_from_legacy_dict_fills_defaults():
    # A v1 record had only id/text/done/created.
    legacy = {"id": 5, "text": "old", "done": True, "created": "2020-01-01T00:00:00+00:00"}
    t = Task.from_dict(legacy)
    assert t.priority == Priority.MEDIUM
    assert t.tags == []
    assert t.due is None


def test_overdue_and_due_soon():
    past = (today() - timedelta(days=1)).isoformat()
    soon = (today() + timedelta(days=1)).isoformat()
    far = (today() + timedelta(days=30)).isoformat()
    assert Task(id=1, text="a", due=past).is_overdue
    assert not Task(id=2, text="b", due=past, done=True).is_overdue
    assert Task(id=3, text="c", due=soon).is_due_soon
    assert not Task(id=4, text="d", due=far).is_due_soon


# --- TaskList --------------------------------------------------------------
def test_add_assigns_ids_and_dedupes_tags():
    tl = TaskList()
    t1 = tl.add("first", tags=["b", "a", "a"])
    t2 = tl.add("second")
    assert t1.id == 1 and t2.id == 2
    assert t1.tags == ["a", "b"]


def test_complete_and_reopen():
    tl = TaskList()
    tl.add("task")
    tl.complete(1)
    assert tl.get(1).done and tl.get(1).completed is not None
    tl.reopen(1)
    assert not tl.get(1).done and tl.get(1).completed is None


def test_remove_and_clear():
    tl = TaskList()
    tl.add("a")
    tl.add("b")
    tl.complete(2)
    assert tl.remove(1) is True
    assert tl.remove(99) is False
    tl.add("c")
    removed = tl.clear(done_only=True)
    assert removed == 1
    assert {t.text for t in tl.tasks} == {"c"}


def test_filter_combinations():
    tl = TaskList()
    tl.add("buy milk", priority=Priority.HIGH, tags=["shop"])
    tl.add("buy bread", priority=Priority.LOW, tags=["shop"])
    tl.add("call mom", priority=Priority.HIGH)
    tl.complete(3)

    assert len(tl.filter()) == 2  # pending only
    assert len(tl.filter(include_done=True)) == 3
    assert len(tl.filter(priority=Priority.HIGH, include_done=True)) == 2
    assert len(tl.filter(tag="shop")) == 2
    assert len(tl.filter(search="milk")) == 1


def test_sort_by_priority_and_due():
    tl = TaskList()
    tl.add("low", priority=Priority.LOW)
    tl.add("high", priority=Priority.HIGH)
    by_pri = TaskList.sort(tl.tasks, by="priority")
    assert [t.text for t in by_pri] == ["high", "low"]


def test_all_tags_counts():
    tl = TaskList()
    tl.add("a", tags=["x", "y"])
    tl.add("b", tags=["x"])
    assert tl.all_tags() == {"x": 2, "y": 1}


def test_stats():
    tl = TaskList()
    tl.add("a", priority=Priority.HIGH)
    tl.add("b")
    tl.complete(2)
    s = tl.stats()
    assert s["total"] == 2 and s["done"] == 1 and s["pending"] == 1
    assert s["by_priority"]["high"] == 1
