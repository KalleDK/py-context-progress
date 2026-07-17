import pytest

pytest.importorskip("rich")

from context_progress import add, remove, subtask, update
from context_progress.richprogress import RichProgress, SProgress, to_rich_description


def test_to_rich_description_depth_and_suffix() -> None:
    assert to_rich_description("download", None, depth=0) == "download"
    assert to_rich_description("download", "metadata", depth=1) == "  download: metadata"


def test_subtask_inserts_child_after_parent() -> None:
    progress = SProgress(disable=True)
    with progress:
        root = RichProgress(progress)
        parent = root.subtask("parent", total=1)
        child = parent.subtask("child", total=1)

        descriptions = [task.description for task in progress.tasks]
        assert descriptions == ["parent", "  child"]

        child.remove()
        parent.remove()


def test_task_update_rewrites_description_with_name_prefix() -> None:
    progress = SProgress(disable=True)
    with progress:
        root = RichProgress(progress)
        task = root.subtask("download", total=2)

        task.update(description="metadata", advance=1)

        rich_task = progress.tasks[0]
        assert rich_task.description == "download: metadata"
        assert rich_task.completed == 1

        task.remove()


def test_session_registers_and_unregisters_backend() -> None:
    with RichProgress.session(disable=True) as backend:
        with subtask("work", total=2):
            update(advance=1)
            assert len(backend.progress.tasks) == 1
            assert backend.progress.tasks[0].completed == 1

    assert len(backend.progress.tasks) == 0


def test_manual_add_and_remove_backend() -> None:
    progress = SProgress(disable=True)
    backend = RichProgress(progress)

    add(backend)
    try:
        with subtask("registered", total=1):
            assert len(progress.tasks) == 1
            update(advance=1)
            assert progress.tasks[0].completed == 1
    finally:
        remove(backend)

    with subtask("removed", total=1):
        assert len(progress.tasks) == 0
