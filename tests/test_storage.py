"""Tests for the storage layer, using a temp data file via TODO_CLI_DATA."""

from __future__ import annotations

import json

import pytest

from todo_cli import storage


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    """Point storage at a throwaway file for each test."""
    data_file = tmp_path / "tasks.json"
    monkeypatch.setenv("TODO_CLI_DATA", str(data_file))
    return data_file


def test_load_empty_when_missing():
    assert storage.load_tasks() == []


def test_save_and_load_roundtrip(temp_data):
    tasks = [{"id": 1, "text": "write tests", "done": False, "created": "x"}]
    storage.save_tasks(tasks)
    assert temp_data.exists()
    assert storage.load_tasks() == tasks


def test_next_id_increments():
    assert storage.next_id([]) == 1
    assert storage.next_id([{"id": 3}, {"id": 7}]) == 8


def test_corrupt_file_returns_empty(temp_data):
    temp_data.parent.mkdir(parents=True, exist_ok=True)
    temp_data.write_text("not valid json {", encoding="utf-8")
    assert storage.load_tasks() == []


def test_save_creates_parent_dir(tmp_path, monkeypatch):
    nested = tmp_path / "a" / "b" / "tasks.json"
    monkeypatch.setenv("TODO_CLI_DATA", str(nested))
    storage.save_tasks([{"id": 1}])
    assert json.loads(nested.read_text()) == [{"id": 1}]
