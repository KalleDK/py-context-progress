"""Rich backend for context_progress.

This module provides a ``TaskP`` implementation backed by ``rich.progress``.
It supports nested subtasks by tracking task IDs in insertion order so child
tasks can be rendered directly under their parent.
"""

import contextlib
import dataclasses
import logging
from collections.abc import Generator
from threading import RLock
from typing import Any, NotRequired, Optional, TypedDict, Union

from rich.console import Console
from rich.progress import GetTimeCallable, Progress, ProgressColumn, Task, TaskID

from context_progress import NOT_SET, NOT_SET_T, TaskP, add, remove

logger = logging.getLogger(__name__)


def to_rich_description(name: str, description: str | None, depth: int) -> str:
    """Build an indented rich task description for nested rendering."""

    return "  " * depth + (name if description is None else f"{name}: {description}")


class SProgress(Progress):
    """Progress subclass with stable, user-controlled task ordering."""

    def __init__(
        self,
        *columns: Union[str, ProgressColumn],
        console: Optional[Console] = None,
        auto_refresh: bool = True,
        refresh_per_second: float = 10,
        speed_estimate_period: float = 30.0,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        get_time: Optional[GetTimeCallable] = None,
        disable: bool = False,
        expand: bool = False,
    ) -> None:
        self._task_ids: list[TaskID] = []
        self._olock = RLock()
        super().__init__(
            *columns,
            console=console,
            auto_refresh=auto_refresh,
            refresh_per_second=refresh_per_second,
            speed_estimate_period=speed_estimate_period,
            transient=transient,
            redirect_stdout=redirect_stdout,
            redirect_stderr=redirect_stderr,
            get_time=get_time,
            disable=disable,
            expand=expand,
        )

    @property
    def task_ids(self) -> list[TaskID]:
        """Task IDs in explicit render order."""

        return self._task_ids

    @property
    def tasks(self) -> list[Task]:
        """Tasks in explicit render order."""

        return [self._tasks[task_id] for task_id in self._task_ids]

    def add_task(
        self,
        description: str,
        start: bool = True,
        total: Optional[float] = 100.0,
        completed: int = 0,
        visible: bool = True,
        **fields: Any,
    ) -> TaskID:
        """Add a new top-level task and append it to render order."""

        with self._olock:
            task_id = super().add_task(description, start, total, completed, visible, **fields)
            self._task_ids.append(task_id)
        return task_id

    def insert_task(
        self,
        parent_task: TaskID,
        description: str,
        start: bool = True,
        total: float | None = 100.0,
        completed: int = 0,
        visible: bool = True,
        **fields: Any,
    ) -> TaskID:
        """Insert a child task directly after its parent in render order."""

        with self._olock:
            logger.debug("insert_task: parent_task=%s, description=%s, total=%s", parent_task, description, total)
            task_id = super().add_task(description, start, total, completed, visible, **fields)
            idx = self._task_ids.index(parent_task)
            self._task_ids.insert(idx + 1, task_id)
        return task_id

    def remove_task(self, task_id: TaskID) -> None:
        with self._olock:
            if task_id in self._task_ids:
                self._task_ids.remove(task_id)
                super().remove_task(task_id)


class UpdateDict(TypedDict):
    description: NotRequired[str | None]
    total: NotRequired[int | None]
    advance: NotRequired[int | None]


@dataclasses.dataclass
class RichTask(TaskP):
    """Concrete task handle used for nested rich progress tasks."""

    progress: SProgress
    task_id: TaskID
    name: str
    depth: int

    def subtask(self, name: str, description: str | None = None, total: int | None = None) -> "TaskP":
        """Create a nested child task rendered below this task."""

        depth = self.depth + 1
        task_id = self.progress.insert_task(self.task_id, to_rich_description(name, description, depth), total=total)
        return RichTask(self.progress, task_id, name, depth)

    def remove(self) -> None:
        """Remove this task from the rich progress display."""

        self.progress.remove_task(self.task_id)

    def update(
        self,
        description: str | NOT_SET_T | None = NOT_SET,
        total: int | NOT_SET_T | None = NOT_SET,
        advance: int | NOT_SET_T | None = NOT_SET,
    ) -> None:
        """Apply updates to the underlying rich task."""

        argv: UpdateDict = {}
        if description is not NOT_SET:
            description = "  " * self.depth + (self.name if description is None else f"{self.name}: {description}")
            argv["description"] = description
        if total is not NOT_SET:
            argv["total"] = total
        if advance is not NOT_SET:
            argv["advance"] = advance

        logger.debug("update: task_id=%s, argv=%s", self.task_id, argv)
        self.progress.update(self.task_id, **argv)


@dataclasses.dataclass
class RichProgress(TaskP):
    """Root progress backend that can be registered in context_progress."""

    progress: SProgress

    @classmethod
    @contextlib.contextmanager
    def session(
        cls,
        *columns: Union[str, ProgressColumn],
        console: Optional[Console] = None,
        auto_refresh: bool = True,
        refresh_per_second: float = 10,
        speed_estimate_period: float = 30.0,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        get_time: Optional[GetTimeCallable] = None,
        disable: bool = False,
        expand: bool = False,
    ) -> Generator["RichProgress", None, None]:
        """Context manager that creates, registers, and unregisters RichProgress."""

        with SProgress(
            *columns,
            console=console,
            auto_refresh=auto_refresh,
            refresh_per_second=refresh_per_second,
            speed_estimate_period=speed_estimate_period,
            transient=transient,
            redirect_stdout=redirect_stdout,
            redirect_stderr=redirect_stderr,
            get_time=get_time,
            disable=disable,
            expand=expand,
        ) as p:
            rp = RichProgress(p)
            add(rp)
            try:
                yield rp
            finally:
                remove(rp)

    def subtask(self, name: str, description: str | None = None, total: int | None = None) -> "TaskP":
        """Create a top-level rich task."""

        task_id = self.progress.add_task(to_rich_description(name, description, depth=0), total=total)
        return RichTask(self.progress, task_id, name, depth=0)

    def remove(self) -> None:
        """No-op for root task compatibility with the TaskP protocol."""

        pass

    def update(
        self,
        description: str | NOT_SET_T | None = NOT_SET,
        total: int | NOT_SET_T | None = NOT_SET,
        advance: int | NOT_SET_T | None = NOT_SET,
    ) -> None:
        """No-op for root task compatibility with the TaskP protocol."""

        pass
