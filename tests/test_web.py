"""API tests for the FastAPI web layer, using a temp data file."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from todo_cli.web.app import app


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_CLI_DATA", str(tmp_path / "tasks.json"))


@pytest.fixture
def client():
    return TestClient(app)


def test_index_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "todo" in res.text.lower()


def test_create_and_list(client):
    res = client.post("/api/tasks", json={"text": "buy milk", "priority": "high"})
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == 1 and body["priority"] == "high"

    res = client.get("/api/tasks")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_create_with_tags_and_due(client):
    res = client.post(
        "/api/tasks",
        json={"text": "ship", "tags": ["work", "work"], "due": "2030-06-01"},
    )
    body = res.json()
    assert body["tags"] == ["work"]
    assert body["due"] == "2030-06-01"


def test_create_invalid_due_returns_400(client):
    res = client.post("/api/tasks", json={"text": "x", "due": "someday"})
    assert res.status_code == 400


def test_create_empty_text_rejected(client):
    res = client.post("/api/tasks", json={"text": ""})
    assert res.status_code == 422  # pydantic validation


def test_get_missing_task_404(client):
    assert client.get("/api/tasks/99").status_code == 404


def test_complete_and_reopen_via_patch(client):
    client.post("/api/tasks", json={"text": "task"})
    res = client.patch("/api/tasks/1", json={"done": True})
    assert res.json()["done"] is True
    assert res.json()["completed"] is not None

    # Pending list hides it; ?all=true shows it.
    assert len(client.get("/api/tasks").json()) == 0
    assert len(client.get("/api/tasks?all=true").json()) == 1

    res = client.patch("/api/tasks/1", json={"done": False})
    assert res.json()["done"] is False


def test_patch_edits_fields(client):
    client.post("/api/tasks", json={"text": "old", "tags": ["a"]})
    res = client.patch(
        "/api/tasks/1",
        json={"text": "new", "priority": "high", "tags": ["b"], "due": ""},
    )
    body = res.json()
    assert body["text"] == "new"
    assert body["priority"] == "high"
    assert body["tags"] == ["b"]
    assert body["due"] is None


def test_filter_and_sort(client):
    client.post("/api/tasks", json={"text": "low", "priority": "low"})
    client.post("/api/tasks", json={"text": "high", "priority": "high"})
    res = client.get("/api/tasks?priority=high")
    assert [t["text"] for t in res.json()] == ["high"]
    res = client.get("/api/tasks?sort=priority")
    assert [t["text"] for t in res.json()] == ["high", "low"]


def test_delete(client):
    client.post("/api/tasks", json={"text": "gone"})
    assert client.delete("/api/tasks/1").status_code == 204
    assert client.delete("/api/tasks/1").status_code == 404


def test_tags_and_stats_endpoints(client):
    client.post("/api/tasks", json={"text": "a", "tags": ["work"], "priority": "high"})
    client.post("/api/tasks", json={"text": "b", "tags": ["work"]})
    assert client.get("/api/tags").json() == {"work": 2}
    stats = client.get("/api/stats").json()
    assert stats["total"] == 2 and stats["pending"] == 2
