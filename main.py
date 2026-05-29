"""Convenience entry point so you can run the app directly.

This lets you start the to-do manager without installing it, e.g.:

    python main.py add "Buy milk"
    python main.py list
    uv run main.py stats

It simply hands control to the Typer app defined in src/todo_cli/cli.py.
The installed `todo` command (see pyproject.toml) runs the same app.
"""

from __future__ import annotations

import os
import sys

# Make `src/` importable when running this file directly (python main.py),
# without needing the package to be installed first.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from todo_cli.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
