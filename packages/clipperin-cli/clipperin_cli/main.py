"""Auto Clipper CLI - Main entry point."""

import sys
from pathlib import Path

import typer
from rich.console import Console

from clipperin_cli import __version__
from clipperin_cli.commands import (
    download_command,
    transcribe_command,
    analyze_command,
    chapters_command,
    render_command,
    config_command,
)

console = Console()

app = typer.Typer(
    name="clipperin",
    help="Clipperin CLI - Create viral shorts from long videos",
    add_completion=True,
    no_args_is_help=True,
)


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
):
    """Clipperin CLI."""
    if version:
        typer.echo(f"clipperin v{__version__}")
        raise typer.Exit()


@app.command()
def download(
    url: str = typer.Argument(..., help="Video URL to download"),
    output: str = typer.Option(None, "-o", "--output", help="Output path"),
    quality: str = typer.Option("good", "-q", "--quality", help="Quality: best, good, medium, low"),
    info_only: bool = typer.Option(False, "--info", help="Show video info only"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Download a video from URL."""
    download_command(url, output, quality, info_only, json_output)


@app.command()
def transcribe(
    input: str = typer.Argument(..., help="Input video or audio file"),
    output: str = typer.Option(None, "-o", "--output", help="Output SRT file"),
    model: str = typer.Option("base", "-m", "--model", help="Whisper model"),
    language: str = typer.Option(None, "-l", "--language", help="Language code"),
    device: str = typer.Option("cpu", "-d", "--device", help="Device: cpu or cuda"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    word_timestamps: bool = typer.Option(False, "--words", help="Word-level timestamps"),
):
    """Transcribe audio to text using Whisper."""
    transcribe_command(input, output, model, language, device, json_output, word_timestamps)


@app.command()
def analyze(
    input: str = typer.Argument(..., help="Input SRT or transcription file"),
    output: str = typer.Option(None, "-o", "--output", help="Output JSON file"),
    ai_provider: str = typer.Option("none", "-a", "--ai", help="AI provider"),
    api_key: str = typer.Option(None, "--api-key", help="API key"),
    min_duration: float = typer.Option(30, "--min-duration", help="Min chapter duration"),
    max_duration: float = typer.Option(90, "--max-duration", help="Max chapter duration"),
):
    """Analyze transcription to extract chapters."""
    analyze_command(input, output, ai_provider, api_key, min_duration, max_duration)


@app.command()
def chapters(
    input: str = typer.Argument(..., help="Chapters JSON file"),
    format: str = typer.Option("table", "-f", "--format", help="Output format"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Detailed info"),
):
    """List chapters from JSON file."""
    chapters_command(input, format, verbose)


@app.command()
def render(
    input_video: str = typer.Argument(..., help="Input video file"),
    chapters: str = typer.Argument(..., help="Chapters JSON file"),
    output_dir: str = typer.Option("./output", "-o", "--output", help="Output directory"),
    chapter_ids: list[str] = typer.Option(None, "-c", "--chapter", help="Chapter IDs"),
    caption_style: str = typer.Option("default", "-s", "--style", help="Caption style"),
    aspect_ratio: str = typer.Option("9:16", "-a", "--aspect", help="Aspect ratio"),
    srt_file: str = typer.Option(None, "-t", "--srt", help="SRT file"),
    hook: bool = typer.Option(False, "-H", "--hook", help="Enable hook overlay"),
    smart_reframe: bool = typer.Option(False, "-R", "--smart-reframe", help="Enable smart reframe"),
    progress_bar: bool = typer.Option(True, "-p", "--progress-bar", help="Progress bar"),
    progress_color: str = typer.Option("#FF0050", "--progress-color", help="Progress color"),
):
    """Render video clips from chapters."""
    render_command(
        input_video, chapters, output_dir, chapter_ids, caption_style,
        aspect_ratio, srt_file, hook, smart_reframe, progress_bar, progress_color,
    )


@app.command()
def config(
    key: str = typer.Argument(None, help="Config key"),
    value: str = typer.Argument(None, help="Config value"),
    list_all: bool = typer.Option(False, "-l", "--list", help="List all config"),
    edit: bool = typer.Option(False, "-e", "--edit", help="Open in editor"),
):
    """Manage configuration."""
    config_command(key, value, list_all, edit)


@app.command("pipeline")
def pipeline_command(
    url: str = typer.Argument(..., help="Video URL"),
    output_dir: str = typer.Option("./output", "-o", "--output", help="Output directory"),
    caption_style: str = typer.Option("default", "-s", "--style", help="Caption style"),
    use_ai: bool = typer.Option(False, "-a", "--ai", help="Use AI analysis"),
):
    """
    Run the full pipeline: download → transcribe → analyze.

    This is a convenience command that combines multiple steps.
    """
    from clipperin_core import Job, VideoDownloader, AudioTranscriber, ContentAnalyzer
    from clipperin_core.ai import GroqClient
    from clipperin_cli.config.settings import load_user_config
    from clipperin_cli.output.progress import progress_bar

    config = load_user_config()

    # Create job
    job = Job(url=url)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold cyan]Starting pipeline for:[/bold cyan] {url}")
    console.print()

    with progress_bar(description="Running pipeline...", total=4) as prog:
        # Download
        prog.update(0, description="Downloading video...")
        downloader = VideoDownloader(output_dir=output_path)
        try:
            video_path = downloader.download(url, output_path=output_path / f"{job.id}.mp4")
            job.video_path = video_path
            console.print(f"[green]✓[/green] Downloaded: {video_path.name}")
        except Exception as e:
            console.print(f"[red]✗[/red] Download failed: {e}")
            raise typer.Exit(1)

        # Transcribe
        prog.update(1, description="Transcribing audio...")
        transcriber = AudioTranscriber(model=config.whisper.model)
        try:
            result = transcriber.transcribe(video_path)
            srt_path = output_path / f"{job.id}.srt"
            transcriber.to_srt(result, srt_path)
            job.srt_path = srt_path
            job.transcription = result.segments
            console.print(f"[green]✓[/green] Transcribed: {result.language}, {result.duration:.0f}s")
        except Exception as e:
            console.print(f"[red]✗[/red] Transcription failed: {e}")
            raise typer.Exit(1)

        # Analyze
        prog.update(2, description="Analyzing content...")
        ai_client = None
        if use_ai:
            match config.ai.provider:
                case "groq":
                    ai_client = GroqClient(api_key=config.ai.groq_api_key)
                case "gemini":
                    from clipperin_core.ai import GeminiClient
                    ai_client = GeminiClient(api_key=config.ai.gemini_api_key)
                case "openai":
                    from clipperin_core.ai import OpenAIClient
                    ai_client = OpenAIClient(api_key=config.ai.openai_api_key)

        analyzer = ContentAnalyzer(ai_client=ai_client)
        transcription_text = " ".join([s.get("text", "") for s in result.segments])

        try:
            chapters = analyzer.analyze_chapters(
                transcription_text,
                result.duration,
                use_ai=use_ai,
            )
            job.chapters = chapters
            console.print(f"[green]✓[/green] Found {len(chapters)} chapters")

            # Save chapters
            import json
            chapters_path = output_path / f"{job.id}_chapters.json"
            with open(chapters_path, "w") as f:
                json.dump({
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
                }, f, indent=2)
            console.print(f"[green]✓[/green] Saved chapters to: {chapters_path.name}")

        except Exception as e:
            console.print(f"[red]✗[/red] Analysis failed: {e}")
            raise typer.Exit(1)

        prog.update(3)

    console.print()
    console.print(f"[bold green]Pipeline complete![/bold green]")
    console.print(f"Next step: Render clips with:")
    console.print(f"  [cyan]clipperin render[/cyan] {video_path.name} {chapters_path.name} -o {output_dir}")


def main_entry():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main_entry()
