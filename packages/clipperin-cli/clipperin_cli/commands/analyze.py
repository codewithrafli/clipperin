"""Analyze command."""

import json
import sys
from pathlib import Path

import typer

from clipperin_core import ContentAnalyzer
from clipperin_core.ai import GeminiClient, GroqClient, OpenAIClient
from clipperin_cli.output.progress import progress_bar


app = typer.Typer(help="Analyze transcription to extract chapters.")


def analyze_command(
    input: str = typer.Argument(..., help="Input SRT or transcription file"),
    output: str = typer.Option(None, "-o", "--output", help="Output JSON file for chapters"),
    ai_provider: str = typer.Option("none", "-a", "--ai", help="AI provider: gemini, groq, openai, none"),
    api_key: str = typer.Option(None, "--api-key", help="API key for AI provider"),
    min_duration: float = typer.Option(30, "--min-duration", help="Minimum chapter duration (seconds)"),
    max_duration: float = typer.Option(90, "--max-duration", help="Maximum chapter duration (seconds)"),
) -> None:
    """
    Analyze transcription to extract chapters and highlights.

    Example:
        clipperin analyze video.srt -o chapters.json --ai groq
    """
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"Error: File not found: {input}", err=True)
        raise typer.Exit(1)

    # Read transcription
    if input_path.suffix == ".srt":
        # Parse SRT
        transcription = _parse_srt(input_path)
    elif input_path.suffix == ".json":
        with open(input_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            transcription = " ".join([s.get("text", "") for s in data])
        else:
            transcription = data.get("text", "")
    else:
        with open(input_path) as f:
            transcription = f.read()

    if not transcription:
        typer.echo("Error: No transcription found", err=True)
        raise typer.Exit(1)

    # Create AI client
    ai_client = None
    if ai_provider != "none":
        match ai_provider:
            case "gemini":
                ai_client = GeminiClient(api_key=api_key)
            case "groq":
                ai_client = GroqClient(api_key=api_key)
            case "openai":
                ai_client = OpenAIClient(api_key=api_key)
            case _:
                typer.echo(f"Warning: Unknown AI provider '{ai_provider}', using rule-based", err=True)

    analyzer = ContentAnalyzer(ai_client=ai_client)

    # Estimate duration (or get from file metadata if available)
    duration = _estimate_duration(transcription)

    with progress_bar(
        description="Analyzing content...",
        total=100,
    ) as progress:
        use_ai = ai_provider != "none" and ai_client and ai_client.is_configured()

        chapters = analyzer.analyze_chapters(
            transcription,
            duration=duration,
            use_ai=use_ai,
        )
        progress.update(100)

    # Output results
    result = {
        "chapters": [
            {
                "id": c.id,
                "title": c.title,
                "start": c.start,
                "end": c.end,
                "duration": c.duration,
                "summary": c.summary,
                "confidence": c.confidence,
                "hooks": c.hooks,
            }
            for c in chapters
        ]
    }

    output_path = Path(output) if output else None
    if output_path:
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        typer.echo(f"Chapters saved to: {output_path}")
    else:
        typer.echo(json.dumps(result, indent=2))


def _parse_srt(srt_path: Path) -> str:
    """Parse SRT file and return full text."""
    import re

    with open(srt_path) as f:
        content = f.read()

    blocks = re.split(r'\n\s*\n', content.strip())
    texts = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            texts.extend(lines[2:])
    return " ".join(texts)


def _estimate_duration(text: str) -> float:
    """Estimate duration from text length."""
    # Average speaking rate: 150 words per minute
    words = len(text.split())
    return (words / 150) * 60
