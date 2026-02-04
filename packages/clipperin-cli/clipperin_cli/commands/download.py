"""Download command."""

import json
from pathlib import Path

import typer

from clipperin_core import VideoDownloader
from clipperin_cli.output.progress import progress_bar


app = typer.Typer(help="Download videos from YouTube and other platforms.")


def download_command(
    url: str = typer.Argument(..., help="Video URL to download"),
    output: str = typer.Option(None, "-o", "--output", help="Output path"),
    quality: str = typer.Option("good", "-q", "--quality", help="Quality: best, good, medium, low"),
    info_only: bool = typer.Option(False, "--info", help="Show video info only"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """
    Download a video from the given URL.

    Example:
        clipperin download "https://youtube.com/watch?v=VIDEO_ID" -o ./video.mp4
    """
    downloader = VideoDownloader(output_dir=Path(output).parent if output else None)

    if info_only:
        info = downloader.get_info(url)
        if not info:
            typer.echo("Failed to get video info", err=True)
            raise typer.Exit(1)

        if json_output:
            typer.echo(json.dumps({
                "id": info.id,
                "title": info.title,
                "duration": info.duration,
                "width": info.width,
                "height": info.height,
                "fps": info.fps,
                "thumbnail": info.thumbnail_url,
            }, indent=2))
        else:
            typer.echo(f"Title: {info.title}")
            typer.echo(f"Duration: {info.duration:.0f}s")
            typer.echo(f"Resolution: {info.width}x{info.height}")
            typer.echo(f"FPS: {info.fps}")
        return

    if not downloader.is_available():
        typer.echo("Error: yt-dlp is not installed", err=True)
        raise typer.Exit(1)

    output_path = Path(output) if output else None

    with progress_bar(
        description=f"Downloading {url[:40]}...",
        total=100,
    ) as progress:
        def callback(p):
            progress.update(p)

        try:
            result = downloader.download(
                url,
                output_path=output_path,
                quality=quality,
                progress_callback=callback,
            )

            if json_output:
                typer.echo(json.dumps({"path": str(result)}, indent=2))
            else:
                typer.echo(f"Downloaded to: {result}")

        except RuntimeError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
