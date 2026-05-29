"""End-to-end tests for the CLI commands via Typer's test runner."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from todo_cli.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_CLI_DATA", str(tmp_path / "tasks.json"))


def run(*args, input=None):
    return runner.invoke(app, list(args), input=input)


def test_add_and_list():
    assert run("add", "buy milk").exit_code == 0
    out = run("list").stdout
    assert "buy milk" in out


def test_add_with_options_and_show():
    run("add", "ship feature", "-p", "high", "-t", "work", "-t", "urgent",
        "-d", "2030-06-01", "-n", "remember the docs")
    out = run("show", "1").stdout
    assert "high" in out and "work" in out and "2030-06-01" in out
    assert "remember the docs" in out


def test_add_invalid_due_fails():
    result = run("add", "bad date", "-d", "someday")
    assert result.exit_code == 1


def test_done_multiple_and_undone():
    run("add", "alpha")
    run("add", "beta")
    result = run("done", "1", "2")
    assert result.exit_code == 0
    assert "alpha" not in run("list").stdout
    # Reopen task 1.
    assert run("undone", "1").exit_code == 0
    assert "alpha" in run("list").stdout


def test_done_unknown_id_fails():
    result = run("done", "99")
    assert result.exit_code == 1


def test_edit_changes_fields():
    run("add", "original", "-t", "old")
    result = run("edit", "1", "--text", "renamed", "-p", "high",
                 "--add-tag", "new", "--remove-tag", "old")
    assert result.exit_code == 0
    out = run("show", "1").stdout
    assert "renamed" in out and "high" in out and "new" in out
    assert "old" not in out.split("Tags")[1].split("\n")[0]


def test_edit_clear_due():
    run("add", "x", "-d", "2030-01-01")
    run("edit", "1", "-d", "none")
    assert "2030-01-01" not in run("show", "1").stdout


def test_filter_by_priority_and_tag():
    run("add", "high one", "-p", "high", "-t", "work")
    run("add", "low one", "-p", "low", "-t", "home")
    out = run("list", "-p", "high").stdout
    assert "high one" in out and "low one" not in out
    out = run("list", "-t", "home").stdout
    assert "low one" in out and "high one" not in out


def test_search():
    run("add", "find the needle")
    run("add", "something else")
    out = run("list", "-s", "needle").stdout
    assert "needle" in out and "something else" not in out


def test_remove_multiple():
    run("add", "a")
    run("add", "b")
    result = run("remove", "1", "2")
    assert result.exit_code == 0
    assert run("list", "--all").stdout.count("│") == 0 or "No matching" in run("list", "--all").stdout


def test_clear_done_only():
    run("add", "keep")
    run("add", "drop")
    run("done", "2")
    result = run("clear", "--done", "--force")
    assert result.exit_code == 0
    assert "keep" in run("list", "--all").stdout
    assert "drop" not in run("list", "--all").stdout


def test_tags_and_stats():
    run("add", "a", "-t", "work", "-p", "high")
    run("add", "b", "-t", "work")
    assert "work" in run("tags").stdout
    out = run("stats").stdout
    assert "Total" in out


def test_export_json_and_csv_and_md():
    run("add", "exported", "-t", "x")
    json_out = run("export", "-f", "json").stdout
    assert json.loads(json_out)[0]["text"] == "exported"

    csv_out = run("export", "-f", "csv").stdout
    assert "exported" in csv_out and "id,text" in csv_out

    md_out = run("export", "-f", "md").stdout
    assert "- [ ]" in md_out and "exported" in md_out


def test_export_to_file(tmp_path):
    run("add", "filed")
    target = tmp_path / "out.json"
    result = run("export", "-f", "json", "-o", str(target))
    assert result.exit_code == 0
    assert "filed" in target.read_text()
