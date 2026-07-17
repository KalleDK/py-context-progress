import asyncio
import logging
import random

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn

from context_progress import subtask, update
from context_progress.richprogress import RichProgress


async def download_file(name: str, total: int, delay: float = 0.2) -> None:
    total = total * 10
    with subtask(name, total=total):
        for i in range(total):
            await asyncio.sleep(delay)
            update(advance=1, description=f"Got {i + 1}/{total}")


async def scrape(index: int) -> None:
    with subtask(f"scrape {index}"):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                download_file(f"scrape {index} file1", total=random.randint(2, 7), delay=random.uniform(0.1, 0.5))
            )
            tg.create_task(
                download_file(f"scrape {index} file2", total=random.randint(2, 7), delay=random.uniform(0.1, 0.5))
            )
            tg.create_task(
                download_file(f"scrape {index} file3", total=random.randint(2, 7), delay=random.uniform(0.1, 0.5))
            )


async def main() -> None:
    console = Console()
    with RichProgress.session(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(download_file("master", total=5))
            tg.create_task(scrape(1))
            tg.create_task(scrape(2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
    asyncio.run(main())
