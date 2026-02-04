"""Video renderer using FFmpeg."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from clipper_core.models.config import OutputConfig, AspectRatio, CaptionStyle


@dataclass
class RenderResult:
    """Result of video rendering."""

    output_path: Path
    duration: float
    width: int
    height: int
    file_size: int
    success: bool
    error: Optional[str] = None

    @property
    def file_size_mb(self) -> float:
        """File size in megabytes."""
        return self.file_size / (1024 * 1024)


class VideoRenderer:
    """
    Render video clips using FFmpeg.

    Handles cropping, resizing, subtitle burning, and more.
    """

    def __init__(self, output_config: Optional[OutputConfig] = None):
        self.config = output_config or OutputConfig()

    def render_clip(
        self,
        input_path: Path,
        output_path: Path,
        start: float,
        end: float,
        caption_style: Optional[CaptionStyle] = None,
        srt_path: Optional[Path] = None,
        enable_hook: bool = False,
        hook_text: str = "",
        enable_smart_reframe: bool = False,
        enable_progress_bar: bool = False,
        progress_bar_color: str = "#FF0050",
        aspect_ratio: AspectRatio = AspectRatio.PORTRAIT,
    ) -> RenderResult:
        """
        Render a video clip with all effects applied.

        Args:
            input_path: Source video path
            output_path: Output video path
            start: Start time in seconds
            end: End time in seconds
            caption_style: Caption style for subtitles
            srt_path: Path to SRT subtitle file
            enable_hook: Whether to add hook overlay
            hook_text: Hook text to display
            enable_smart_reframe: Whether to center on faces
            enable_progress_bar: Whether to add progress bar
            progress_bar_color: Color of progress bar
            aspect_ratio: Output aspect ratio

        Returns:
            RenderResult with output info
        """
        duration = end - start
        width, height = self.config.dimensions

        # Build FFmpeg filter chain
        filters = []
        filter_complex = []

        # 1. Trim and set speed
        filters.append(f"[0:v]trim={start}:{end},setpts=PTS-STARTPTS[v1]")

        # 2. Smart reframe (face tracking)
        if enable_smart_reframe:
            filters.append(self._build_reframe_filter("[v1]", width, height))
        else:
            # Simple center crop
            filters.append(f"[v1]crop={self.config.width}:{self.config.height}:(iw-{self.config.width})/2:(ih-{self.config.height})/2,scale={width}:{height}[v2]")

        # 3. Progress bar
        if enable_progress_bar:
            filter_complex.append(self._build_progress_bar_filter(width, height, progress_bar_color, duration))

        # 4. Subtitles
        if srt_path and caption_style:
            filters.append(self._build_subtitle_filter(srt_path, caption_style))

        # 5. Hook overlay
        if enable_hook and hook_text:
            filter_complex.append(self._build_hook_filter(hook_text, width, height, caption_style))

        # Combine all filters
        full_filter = self._combine_filters(filters, filter_complex)

        # Build command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-ss", str(start),
            "-i", str(input_path),
            "-t", str(duration),
            "-vf", full_filter,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(self.config.crf),
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if output_path.exists():
                info = self._get_video_info(output_path)
                return RenderResult(
                    output_path=output_path,
                    duration=info.get("duration", duration),
                    width=info.get("width", width),
                    height=info.get("height", height),
                    file_size=output_path.stat().st_size,
                    success=True,
                )
            else:
                return RenderResult(
                    output_path=output_path,
                    duration=duration,
                    width=width,
                    height=height,
                    file_size=0,
                    success=False,
                    error="Output file not created",
                )

        except subprocess.CalledProcessError as e:
            return RenderResult(
                output_path=output_path,
                duration=duration,
                width=width,
                height=height,
                file_size=0,
                success=False,
                error=e.stderr,
            )

    def _build_reframe_filter(self, input_label: str, width: int, height: int) -> str:
        """Build smart reframe filter for face tracking."""
        # Use FFmpeg's crop detection with smoothing
        return (
            f"{input_label}"
            f",cropdetect=24:16:0"
            f",crop={self.config.width}:{self.config.height}"
            f",scale={width}:{height}"
        )

    def _build_subtitle_filter(self, srt_path: Path, style: CaptionStyle) -> str:
        """Build subtitle burning filter."""
        # FFmpeg drawtext filter for each subtitle word
        # This is a simplified version - real implementation would parse SRT
        force_style = f"FontName={style.font_name},FontSize={style.font_size},PrimaryColour=&H{self._color_to_ass(style.font_color)}"

        if style.outline:
            force_style += f",Outline={style.outline},BackColour=&H{self._color_to_ass(style.outline_color)}"

        return f"subtitles={srt_path}:force_style='{force_style}'"

    def _build_progress_bar_filter(self, width: int, height: int, color: str, duration: float) -> str:
        """Build progress bar filter."""
        bar_height = self.config.progress_bar_height
        y_pos = height - bar_height - 20

        # Animated progress bar
        return (
            f"color=c={color}:s={width}x{bar_height}[bar];"
            f"[bar]drawbox=w=(t/{duration})*iw:h=ih:t=0:c=white@0.3[progress];"
        )

    def _build_hook_filter(self, text: str, width: int, height: int, style: CaptionStyle) -> str:
        """Build hook text overlay filter."""
        font_size = int(style.font_size * 1.2)
        y_pos = height // 3

        # Escape special characters
        escaped_text = text.replace("'", "'\\\\\\'").replace(":", "\\:")

        return (
            f"drawtext=text='{escaped_text}':"
            f"fontsize={font_size}:"
            f"fontcolor={style.font_color}:"
            f"x=(w-tw)/2:y={y_pos}:"
            f"fontfile={style.font_name}:"
            f"textbox=1:box=1:boxcolor={style.background_color}:"
            f"boxborderw=10"
        )

    def _combine_filters(self, filters: List[str], filter_complex: List[str]) -> str:
        """Combine all filters into FFmpeg filter string."""
        if filter_complex:
            return ";".join(filters) + ";" + ";".join(filter_complex)
        return ";".join(filters)

    def _color_to_ass(self, color: str) -> str:
        """Convert color name/hex to ASS format."""
        if color.startswith("#"):
            color = color[1:]
        if len(color) == 6:
            # Convert RGB to BGR (ASS format)
            return color[4:6] + color[2:4] + color[0:2]
        return "FFFFFF"  # Default white

    def _get_video_info(self, path: Path) -> dict:
        """Get video file information."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json",
            str(path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            data = json.loads(result.stdout)
            stream = data.get("streams", [{}])[0]
            return {
                "width": stream.get("width"),
                "height": stream.get("height"),
                "duration": float(stream.get("duration", 0)),
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            return {}

    def generate_thumbnail(
        self,
        input_path: Path,
        output_path: Path,
        timestamp: float = 0.0,
        width: int = 360,
    ) -> bool:
        """
        Generate a thumbnail from video.

        Args:
            input_path: Source video
            output_path: Output image path
            timestamp: Time to capture thumbnail at
            width: Thumbnail width

        Returns:
            True if successful
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(timestamp),
            "-i", str(input_path),
            "-vframes", "1",
            "-vf", f"scale={width}:-1",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path.exists()
        except subprocess.CalledProcessError:
            return False

    def is_available(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
