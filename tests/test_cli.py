"""End-to-end tests for the CLI commands via Typer's test runner."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from todo_cli.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_CLI_DATA", str(tmp_path / "tasks.json"))


def test_add_and_list():
    result = runner.invoke(app, ["add", "buy milk"])
    assert result.exit_code == 0
    assert "Added" in result.stdout

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "buy milk" in result.stdout


def test_done_marks_complete():
    runner.invoke(app, ["add", "task one"])
    result = runner.invoke(app, ["done", "1"])
    assert result.exit_code == 0
    assert "Completed" in result.stdout

    # Pending list should hide it; --all should show it.
    assert "task one" not in runner.invoke(app, ["list"]).stdout
    assert "task one" in runner.invoke(app, ["list", "--all"]).stdout


def test_done_unknown_id_fails():
    result = runner.invoke(app, ["done", "99"])
    assert result.exit_code == 1
    assert "No task" in result.stdout


def test_remove():
    runner.invoke(app, ["add", "throwaway"])
    result = runner.invoke(app, ["remove", "1"])
    assert result.exit_code == 0
    assert "Removed" in result.stdout
    assert "throwaway" not in runner.invoke(app, ["list", "--all"]).stdout


def test_clear_force():
    runner.invoke(app, ["add", "a"])
    runner.invoke(app, ["add", "b"])
    result = runner.invoke(app, ["clear", "--force"])
    assert result.exit_code == 0
    assert "No tasks" in runner.invoke(app, ["list", "--all"]).stdout
