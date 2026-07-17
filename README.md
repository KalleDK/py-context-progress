# Context Progress

Context Progress lets you emit progress updates from anywhere in a call chain
without passing progress objects through every function.

It uses a context-local task stack, so nested work can report progress via a
small global API.

## Install

Base package:

```bash
uv add context-progress
```

With Rich integration:

```bash
uv add 'context-progress[rich]'
```

## Core API

- `add(backend)`: register a backend for the current context.
- `remove(backend)`: unregister a backend.
- `subtask(name, description=None, total=None)`: create a nested task scope.
- `update(description=..., total=..., advance=...)`: push updates to all active
  backends.

## RichProgress

`context_progress.richprogress.RichProgress` is a Rich backend for the core API.

Use `RichProgress.session(...)` for the simplest setup. It creates an
`SProgress` instance, registers the backend on enter, and unregisters it on
exit.

```python
from time import sleep

from rich.progress import BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn

from context_progress import subtask, update
from context_progress.richprogress import RichProgress


def run_step(description: str, total: int, delay: float = 0.1) -> None:
	update(description=description)
	for _ in range(total):
		sleep(delay)
		update(advance=1)


with RichProgress.session(
	TextColumn("[progress.description]{task.description}"),
	BarColumn(),
	TaskProgressColumn(),
	TimeElapsedColumn(),
):
	with subtask("download", total=2):
		run_step("metadata", total=2)
		with subtask("artifacts", total=3):
			run_step("files", total=3)
```

For a complete runnable example, see `examples/richprogress.py`.

## RichProgress Behavior

- Nested subtasks are indented for readability.
- Child tasks are inserted directly after their parent in render order.
- Updating a `RichTask` description keeps the task name as a prefix.
