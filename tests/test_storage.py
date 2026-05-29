"""Tests for the storage layer, using a temp data file via TODO_CLI_DATA."""

from __future__ import annotations

import json

import pytest

from todo_cli import storage
from todo_cli.models import TaskList


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    """Point storage at a throwaway file for each test."""
    data_file = tmp_path / "tasks.json"
    monkeypatch.setenv("TODO_CLI_DATA", str(data_file))
    return data_file


def test_load_empty_when_missing():
    assert storage.load().tasks == []


def test_save_and_load_roundtrip(temp_data):
    tl = TaskList()
    tl.add("write tests", tags=["dev"])
    storage.save(tl)

    on_disk = json.loads(temp_data.read_text())
    assert on_disk["version"] == storage.SCHEMA_VERSION
    assert len(on_disk["tasks"]) == 1

    reloaded = storage.load()
    assert reloaded.tasks[0].text == "write tests"
    assert reloaded.tasks[0].tags == ["dev"]


def test_reads_legacy_v1_array(temp_data):
    """A bare JSON array (the old format) should still load."""
    temp_data.parent.mkdir(parents=True, exist_ok=True)
    legacy = [{"id": 1, "text": "legacy task", "done": False, "created": "2020-01-01T00:00:00+00:00"}]
    temp_data.write_text(json.dumps(legacy), encoding="utf-8")

    tl = storage.load()
    assert len(tl.tasks) == 1
    assert tl.tasks[0].text == "legacy task"
    assert tl.tasks[0].priority.value == "medium"  # default filled in


def test_corrupt_file_returns_empty(temp_data):
    temp_data.parent.mkdir(parents=True, exist_ok=True)
    temp_data.write_text("not valid json {", encoding="utf-8")
    assert storage.load().tasks == []


def test_save_creates_parent_dir(tmp_path, monkeypatch):
    nested = tmp_path / "a" / "b" / "tasks.json"
    monkeypatch.setenv("TODO_CLI_DATA", str(nested))
    tl = TaskList()
    tl.add("nested")
    storage.save(tl)
    assert nested.exists()
