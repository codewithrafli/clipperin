"""Render command."""

import json
from pathlib import Path

import typer

from clipperin_core import VideoRenderer, CaptionRenderer
from clipperin_core.models.config import OutputConfig, AspectRatio, CaptionStyle
from clipperin_cli.output.progress import progress_bar


app = typer.Typer(help="Render video clips from chapters.")


def render_command(
    input_video: str = typer.Argument(..., help="Input video file"),
    chapters: str = typer.Argument(..., help="Chapters JSON file"),
    output_dir: str = typer.Option("./output", "-o", "--output", help="Output directory"),
    chapter_ids: list[str] = typer.Option(None, "-c", "--chapter", help="Chapter IDs to render (default: all)"),
    caption_style: str = typer.Option("default", "-s", "--style", help="Caption style"),
    aspect_ratio: str = typer.Option("9:16", "-a", "--aspect", help="Aspect ratio: 9:16, 1:1, 4:5"),
    srt_file: str = typer.Option(None, "-t", "--srt", help="SRT subtitle file"),
    hook: bool = typer.Option(False, "-H", "--hook", help="Enable viral hook overlay"),
    smart_reframe: bool = typer.Option(False, "-R", "--smart-reframe", help="Enable smart reframe"),
    progress_bar: bool = typer.Option(True, "-p", "--progress-bar", help="Enable progress bar"),
    progress_color: str = typer.Option("#FF0050", "--progress-color", help="Progress bar color"),
) -> None:
    """
    Render video clips from chapters.

    Example:
        clipperin render video.mp4 chapters.json -o ./clips -c chapter_id_1
    """
    input_path = Path(input_video)
    chapters_path = Path(chapters)

    if not input_path.exists():
        typer.echo(f"Error: Video not found: {input_video}", err=True)
        raise typer.Exit(1)

    if not chapters_path.exists():
        typer.echo(f"Error: Chapters file not found: {chapters}", err=True)
        raise typer.Exit(1)

    # Load chapters
    with open(chapters_path) as f:
        data = json.load(f)

    all_chapters = data.get("chapters", [])
    if not all_chapters:
        typer.echo("Error: No chapters found", err=True)
        raise typer.Exit(1)

    # Filter chapters
    chapters_to_render = all_chapters
    if chapter_ids:
        chapters_to_render = [c for c in all_chapters if c.get("id") in chapter_ids]
        if not chapters_to_render:
            typer.echo(f"Error: No matching chapters found for IDs: {chapter_ids}", err=True)
            raise typer.Exit(1)

    # Parse aspect ratio
    aspect = AspectRatio.PORTRAIT
    if aspect_ratio == "1:1":
        aspect = AspectRatio.SQUARE
    elif aspect_ratio == "4:5":
        aspect = AspectRatio.VERTICAL

    # Get caption style
    cap_style = None
    for style in CaptionStyle.get_default_styles():
        if style.id == caption_style:
            cap_style = style
            break

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Setup renderer
    config = OutputConfig(
        aspect_ratio=aspect,
        enable_progress_bar=progress_bar,
        progress_bar_color=progress_color,
    )
    renderer = VideoRenderer(output_config=config)

    if not renderer.is_available():
        typer.echo("Error: FFmpeg is not installed", err=True)
        raise typer.Exit(1)

    # SRT path
    srt_path = Path(srt_file) if srt_file else None
    if srt_path and not srt_path.exists():
        typer.echo(f"Warning: SRT file not found: {srt_file}", err=True)
        srt_path = None

    # Render clips
    rendered = []

    with progress_bar(
        description=f"Rendering {len(chapters_to_render)} clips...",
        total=len(chapters_to_render),
    ) as prog:
        for i, chapter in enumerate(chapters_to_render):
            prog.update(i, description=f"Rendering: {chapter.get('title', 'Clip')[:30]}...")

            clip_filename = f"clip_{chapter['id'][:8]}.mp4"
            clip_path = output_path / clip_filename

            # Get hook text
            hook_text = ""
            if hook and chapter.get("hooks"):
                hook_text = chapter["hooks"][0]

            result = renderer.render_clip(
                input_path=input_path,
                output_path=clip_path,
                start=chapter["start"],
                end=chapter["end"],
                caption_style=cap_style,
                srt_path=srt_path,
                enable_hook=hook,
                hook_text=hook_text,
                enable_smart_reframe=smart_reframe,
                enable_progress_bar=progress_bar,
                progress_bar_color=progress_color,
                aspect_ratio=aspect,
            )

            if result.success:
                # Generate thumbnail
                thumb_path = output_path / f"thumb_{chapter['id'][:8]}.jpg"
                renderer.generate_thumbnail(clip_path, thumb_path)

                rendered.append({
                    "path": str(clip_path),
                    "thumbnail": str(thumb_path) if thumb_path.exists() else None,
                    "duration": result.duration,
                    "file_size": result.file_size_mb,
                })
            else:
                typer.echo(f"Warning: Failed to render {chapter.get('title', 'clip')}", err=True)

        prog.update(len(chapters_to_render))

    typer.echo(f"\nRendered {len(rendered)} clips to: {output_path}")

    for clip in rendered:
        typer.echo(f"  - {clip['path']}: {clip['duration']:.0f}s, {clip['file_size']:.1f}MB")
