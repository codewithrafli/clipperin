"""Table output formatting."""

from typing import List, Any
from rich.console import Console
from rich.table import Table as RichTable


console = Console()


def print_table(headers: List[str], rows: List[List[str]], title: str = None) -> None:
    """
    Print data as a formatted table.

    Args:
        headers: Column headers
        rows: Table rows
        title: Optional table title
    """
    table = RichTable(title=title)
    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*row)

    console.print(table)


def print_jobs(jobs: List[Any]) -> None:
    """Print jobs as a table."""
    from clipperin_core.models.job import JobStatus

    headers = ["ID", "URL", "Status", "Progress", "Clips"]
    rows = []

    for job in jobs:
        status_emoji = {
            JobStatus.PENDING: "⏳",
            JobStatus.DOWNLOADING: "📥",
            JobStatus.TRANSCRIBING: "🎧",
            JobStatus.ANALYZING: "🧠",
            JobStatus.CHAPTERS_READY: "✨",
            JobStatus.PROCESSING: "⚙️",
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌",
        }

        emoji = status_emoji.get(job.status, "❓")

        rows.append([
            job.id[:8],
            job.url[:40] + "..." if len(job.url) > 40 else job.url,
            f"{emoji} {job.status}",
            f"{job.progress:.0f}%",
            str(len(job.clips)),
        ])

    print_table(headers, rows)


def print_chapters(chapters: List[Any]) -> None:
    """Print chapters as a table."""
    headers = ["#", "Title", "Start", "End", "Duration", "Score"]
    rows = []

    for i, chapter in enumerate(chapters):
        rows.append([
            str(i + 1),
            chapter.title[:30],
            chapter.start_formatted,
            chapter.end_formatted,
            f"{chapter.duration:.0f}s",
            f"{chapter.confidence:.0%}",
        ])

    print_table(headers, rows)
