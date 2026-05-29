# todo-cli

A friendly, full-featured command-line to-do manager — built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/), managed with [uv](https://docs.astral.sh/uv/).

This is project #1 in a series of Python projects, progressing from basic to advanced.

## Features

- **Priorities** — low / medium / high, color-coded
- **Due dates** — absolute (`2030-06-01`), keywords (`today`, `tomorrow`), or relative (`+3d`, `+2w`, `+1m`); overdue tasks are highlighted
- **Tags** — attach multiple tags, filter and count them
- **Notes** — a longer description per task
- **Filter & search** — by priority, tag, free text, or overdue status
- **Sort** — by id, priority, due date, or creation time
- **Edit** — change any field, add/remove tags, clear the due date
- **Detail view, stats, and tag summary**
- **Export** — JSON, CSV, or Markdown (to stdout or a file)
- Tasks persist as JSON in `~/.todo-cli/tasks.json`; installs as a real `todo` command

## Install & run

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/mahiprime2001/todo-cli.git
cd todo-cli
uv sync                 # create the venv and install dependencies
uv run todo --help      # run without activating anything
```

### Optional: install as a global command

```bash
uv tool install .       # then just use `todo` anywhere
```

## Usage

```bash
# Adding
todo add "Buy milk"
todo add "Ship release" -p high -t work -t urgent -d 2030-06-01 -n "tag the commit"
todo add "Pay rent" --due tomorrow
todo add "Plan trip" --due +2w

# Viewing
todo list                       # pending tasks
todo list --all                 # include completed
todo list -p high               # only high priority
todo list -t work               # only the "work" tag
todo list -s milk               # search text + notes
todo list --overdue             # only overdue
todo list --sort due            # sort by id | priority | due | created
todo show 1                     # full detail of one task

# Changing
todo done 1 2 3                 # complete one or many
todo undone 1                   # reopen a completed task
todo edit 1 --text "New title" -p high --add-tag home --remove-tag work
todo edit 1 -d none             # clear the due date
todo remove 4 5                 # delete one or many

# Insight & export
todo tags                       # all tags with counts
todo stats                      # summary (pending/done/overdue/by priority)
todo export -f md               # json | csv | md to stdout
todo export -f json -o tasks.json

# Cleanup
todo clear --done               # remove completed tasks
todo clear --force              # remove everything (no prompt)
```

Override the storage location with the `TODO_CLI_DATA` environment variable
(handy for testing or keeping separate lists).

## Development

```bash
uv sync                  # install runtime + dev dependencies
uv run pytest            # run the test suite (33 tests)
```

## Project layout

```
todo-cli/
├── pyproject.toml           # project metadata, deps, entry point
├── src/todo_cli/
│   ├── cli.py               # Typer commands (presentation only)
│   ├── models.py            # Task + TaskList: all business logic
│   └── storage.py           # JSON persistence (versioned, backward-compatible)
└── tests/                   # pytest suite (models, storage, CLI)
```

## Data format

Tasks are stored as `{"version": 2, "tasks": [ ... ]}`. The older bare-array
format (version 1) is still read automatically and upgraded on the next save.

## License

MIT
