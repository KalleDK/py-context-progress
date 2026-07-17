from time import sleep

from rich.progress import BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn

from context_progress import add, remove, subtask, update
from context_progress.richprogress import RichProgress, SProgress


def run_step(description: str, total: int, delay: float = 0.5) -> None:
    update(description=description)
    for _ in range(total):
        sleep(delay)
        update(advance=1)


def main() -> None:
    progress = SProgress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )

    with progress:
        rich_progress = RichProgress(progress)
        add(rich_progress)
        try:
            with subtask("download", total=5):
                run_step("fetching metadata", total=3)
                with subtask("artifacts", total=5):
                    run_step("downloading files", total=5)

            with subtask("process", total=4):
                run_step("parsing results", total=2)
                run_step("writing output", total=2)
        finally:
            remove(rich_progress)


if __name__ == "__main__":
    main()
