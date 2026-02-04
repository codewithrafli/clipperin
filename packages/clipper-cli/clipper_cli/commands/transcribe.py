"""Transcribe command."""

import json
from pathlib import Path

import typer

from clipper_core import AudioTranscriber, WhisperModel
from clipper_cli.output.progress import progress_bar


app = typer.Typer(help="Transcribe audio to text using Whisper.")


def transcribe_command(
    input: str = typer.Argument(..., help="Input video or audio file"),
    output: str = typer.Option(None, "-o", "--output", help="Output SRT file"),
    model: str = typer.Option("base", "-m", "--model", help="Whisper model: tiny, base, small, medium, large"),
    language: str = typer.Option(None, "-l", "--language", help="Language code (e.g., en, id, ms)"),
    device: str = typer.Option("cpu", "-d", "--device", help="Device: cpu or cuda"),
    json_output: bool = typer.Option(False, "--json", help="Output transcription as JSON"),
    word_timestamps: bool = typer.Option(False, "--words", help="Include word-level timestamps"),
) -> None:
    """
    Transcribe audio to text using Whisper.

    Example:
        clipper transcribe video.mp4 -o video.srt
    """
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"Error: File not found: {input}", err=True)
        raise typer.Exit(1)

    # Parse model
    try:
        whisper_model = WhisperModel(model)
    except ValueError:
        typer.echo(f"Error: Invalid model '{model}'. Choose from: tiny, base, small, medium, large", err=True)
        raise typer.Exit(1)

    transcriber = AudioTranscriber(
        model=whisper_model,
        language=language or None,
        device=device,
    )

    with progress_bar(
        description="Transcribing...",
        total=100,
    ) as progress:
        def callback(p):
            progress.update(p)

        try:
            result = transcriber.transcribe(input_path, progress_callback=callback)

            # Determine output path
            output_path = Path(output) if output else input_path.with_suffix(".srt")

            # Save SRT
            transcriber.to_srt(result, output_path)

            if json_output:
                typer.echo(json.dumps({
                    "text": result.text,
                    "language": result.language,
                    "duration": result.duration,
                    "segments": result.segments,
                }, indent=2))
            elif word_timestamps:
                words = transcriber.transcribe_with_timestamps(input_path)
                typer.echo(json.dumps(words, indent=2))
            else:
                typer.echo(f"Transcribed to: {output_path}")
                typer.echo(f"Language: {result.language}")
                typer.echo(f"Duration: {result.duration:.0f}s")

        except RuntimeError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
