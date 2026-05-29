# todo-cli

A simple, friendly command-line to-do manager — built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/), managed with [uv](https://docs.astral.sh/uv/).

This is project #1 in a series of Python projects, progressing from basic to advanced.

## Features

- Add, list, complete, and remove tasks
- Pretty terminal tables with status colors
- Tasks persist as JSON in `~/.todo-cli/tasks.json`
- Installable as a real `todo` command

## Install & run

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
# Install dependencies into a managed virtual environment
uv sync

# Run via uv (no activation needed)
uv run todo --help
```

## Usage

```bash
todo add "Buy milk"          # add a task
todo list                    # show pending tasks
todo list --all              # include completed tasks
todo done 1                  # mark task #1 complete
todo remove 2                # delete task #2
todo clear --force           # delete everything
```

Override the storage location with the `TODO_CLI_DATA` environment variable
(handy for testing or keeping separate lists).

## Development

```bash
uv sync                      # install runtime + dev dependencies
uv run pytest                # run the test suite
```

## Project layout

```
todo-cli/
├── pyproject.toml           # project metadata, deps, entry point
├── src/todo_cli/
│   ├── cli.py               # Typer commands
│   └── storage.py           # JSON persistence
└── tests/                   # pytest suite
```

## License

MIT
