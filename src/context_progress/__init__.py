"""Context-local progress fan-out.

This module keeps a stack of active progress backends in a ContextVar so
progress updates can be emitted from deep call chains without passing
progress objects through every function signature.
"""

import contextlib
import contextvars
import dataclasses
import enum
from collections.abc import Generator
from typing import Literal, Protocol

__version__ = "0.1.2"


class NotSet(enum.Enum):
    """Sentinel enum used to detect omitted update arguments."""

    NOT_SET = 0


NOT_SET_T = Literal[NotSet.NOT_SET]
NOT_SET = NotSet.NOT_SET

progress_root: contextvars.ContextVar["TaskHandler"]

__all__ = [
    "NOT_SET",
    "NOT_SET_T",
    "TaskP",
    "add",
    "remove",
    "subtask",
    "update",
]


class TaskP(Protocol):
    """Interface implemented by progress backends used by this package."""

    def subtask(self, name: str, description: str | None = None, total: int | None = None) -> "TaskP": ...

    def remove(self) -> None: ...

    def update(
        self,
        description: str | NOT_SET_T | None = NOT_SET,
        total: int | NOT_SET_T | None = NOT_SET,
        advance: int | NOT_SET_T | None = NOT_SET,
    ) -> None: ...


@dataclasses.dataclass
class TaskHandler:
    """Holds active tasks for the current context and subtask accounting."""

    _tasks: list[TaskP]
    _start_total: int | None
    _subtask_total: int = 0
    _user_total: int = 0

    def _effective_total(self) -> int:
        """Return the externally visible total for top-level tasks."""

        return self._user_total + self._subtask_total

    def add(self, progress: TaskP) -> None:
        self._tasks.append(progress)

    def remove(self, progress: TaskP) -> None:
        self._tasks.remove(progress)

    def update(
        self,
        description: str | NOT_SET_T | None = NOT_SET,
        total: int | NOT_SET_T | None = NOT_SET,
        advance: int | NOT_SET_T | None = NOT_SET,
    ) -> None:
        """Fan out an update to all active tasks in the current context."""

        if isinstance(total, int):
            self._user_total = total
            total = self._effective_total()

        for task in self._tasks:
            task.update(description, total, advance)

    @contextlib.contextmanager
    def subtask(
        self, name: str, description: str | None = None, total: int | None = None
    ) -> Generator[None, None, None]:
        """Create a nested subtask context and advance parent tasks on exit."""

        if not self._tasks:
            yield
            return

        # Top-level handlers account for each child subtask as one extra parent unit.
        if self._start_total is None:
            self._subtask_total += 1
            for task in self._tasks:
                task.update(total=self._effective_total())

        sub_tasks = [task.subtask(name, description, total) for task in self._tasks]
        token = progress_root.set(TaskHandler(sub_tasks, total))
        try:
            yield
        finally:
            progress_root.reset(token)
            for task in sub_tasks:
                task.remove()
            for task in self._tasks:
                task.update(advance=1)


progress_root = contextvars.ContextVar("progress_root", default=TaskHandler([], None))


def _handler() -> TaskHandler:
    """Return the TaskHandler bound to the current context."""

    return progress_root.get()


def update(
    description: str | NOT_SET_T | None = NOT_SET,
    total: int | NOT_SET_T | None = NOT_SET,
    advance: int | NOT_SET_T | None = NOT_SET,
) -> None:
    """Update all progress backends registered for the current context."""

    _handler().update(description, total, advance)


@contextlib.contextmanager
def subtask(name: str, description: str | None = None, total: int | None = None) -> Generator[None, None, None]:
    """Create a nested progress scope for all active backends."""

    with _handler().subtask(name, description, total):
        yield


def add(progress: TaskP) -> None:
    """Register a progress backend for the current context."""

    _handler().add(progress)


def remove(progress: TaskP) -> None:
    """Unregister a progress backend for the current context."""

    _handler().remove(progress)
