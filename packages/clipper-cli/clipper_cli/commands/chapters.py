"""Chapters command."""

import json
from pathlib import Path

import typer

from clipper_cli.output.table import print_table


app = typer.Typer(help="List and manage video chapters.")


def chapters_command(
    input: str = typer.Argument(..., help="Chapters JSON file"),
    format: str = typer.Option("table", "-f", "--format", help="Output format: table, json"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed info"),
) -> None:
    """
    List chapters from a chapters JSON file.

    Example:
        clipper chapters chapters.json
    """
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"Error: File not found: {input}", err=True)
        raise typer.Exit(1)

    with open(input_path) as f:
        data = json.load(f)

    chapters = data.get("chapters", [])

    if not chapters:
        typer.echo("No chapters found")
        return

    if format == "json":
        typer.echo(json.dumps(chapters, indent=2))
        return

    # Table format
    headers = ["#", "Title", "Time", "Duration", "Score"]
    rows = []

    for i, chapter in enumerate(chapters):
        time_str = f"{_format_time(chapter['start'])} - {_format_time(chapter['end'])}"
        duration_str = _format_duration(chapter['duration'])

        if verbose:
            score = f"{chapter.get('confidence', 0):.0%}"
        else:
            score = ""

        rows.append([
            str(i + 1),
            chapter.get('title', 'Untitled')[:30],
            time_str,
            duration_str,
            score,
        ])

        if verbose and chapter.get('summary'):
            rows.append([
                "",
                f"  {chapter['summary'][:50]}...",
                "",
                "",
                "",
            ])

    print_table(headers, rows)


def _format_time(seconds: float) -> str:
    """Format time as MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def _format_duration(seconds: float) -> str:
    """Format duration."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
