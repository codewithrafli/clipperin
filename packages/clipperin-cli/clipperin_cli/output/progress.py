"""Progress bar utilities."""

from contextlib import contextmanager
from typing import Optional, Callable

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

console = Console()


@contextmanager
def progress_bar(
    description: str = "Processing...",
    total: Optional[int] = None,
    console_obj=None,
):
    """
    Create a progress bar context manager.

    Args:
        description: Description text
        total: Total value (100 for percentage)
        console_obj: Optional Rich console

    Yields:
        ProgressBar object
    """
    console_instance = console_obj or console

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console_instance,
    )

    with progress:
        task = progress.add_task(description, total=total)
        yield ProgressBar(progress, task)


class ProgressBar:
    """Wrapper for Rich progress bar."""

    def __init__(self, progress, task_id):
        self.progress = progress
        self.task_id = task_id

    def update(self, value: int, description: str = None) -> None:
        """
        Update progress.

        Args:
            value: Progress value
            description: Optional new description
        """
        kwargs = {"completed": value}
        if description:
            kwargs["description"] = description

        self.progress.update(self.task_id, **kwargs)

    def advance(self, amount: int = 1) -> None:
        """Advance progress by amount."""
        self.progress.advance(self.task_id, amount)


class Spinner:
    """Simple spinner for indeterminate progress."""

    def __init__(self, text: str = "Loading..."):
        self.text = text
        self._progress = None
        self._task = None

    def __enter__(self):
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console,
        )
        self._progress.__enter__()
        self._task = self._progress.add_task(self.text)
        return self

    def __exit__(self, *args):
        self._progress.__exit__(*args)

    def update(self, text: str):
        """Update spinner text."""
        if self._progress and self._task is not None:
            self._progress.update(self._task, description=text)
