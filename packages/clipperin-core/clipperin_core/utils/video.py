"""Video utilities."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VideoInfo:
    """Information about a video file."""

    id: str
    title: str
    duration: float
    width: int
    height: int
    fps: float
    codec: str
    thumbnail_url: Optional[str] = None
    uploader: Optional[str] = None

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio."""
        return self.width / self.height if self.height > 0 else 1.0

    @property
    def is_vertical(self) -> bool:
        """Check if video is vertical (9:16)."""
        return self.aspect_ratio < 1.0


def get_video_info(url_or_path: str) -> Optional[VideoInfo]:
    """
    Get video information from URL or file path.

    Args:
        url_or_path: YouTube URL or local file path

    Returns:
        VideoInfo or None if failed
    """
    if url_or_path.startswith(("http://", "https://")):
        return _get_remote_video_info(url_or_path)
    return _get_local_video_info(Path(url_or_path))


def _get_remote_video_info(url: str) -> Optional[VideoInfo]:
    """Get info for remote video using yt-dlp."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        return VideoInfo(
            id=data.get("id", ""),
            title=data.get("title", "Unknown"),
            duration=float(data.get("duration", 0)),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            fps=float(data.get("fps", 30)),
            codec=data.get("vcodec", "h264"),
            thumbnail_url=data.get("thumbnail"),
            uploader=data.get("uploader"),
        )
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
        return None


def _get_local_video_info(path: Path) -> Optional[VideoInfo]:
    """Get info for local video using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,r_frame_rate",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        stream = data.get("streams", [{}])[0]
        format_data = data.get("format", {})

        # Parse framerate (e.g., "30000/1001")
        fps_str = stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)

        return VideoInfo(
            id=path.stem,
            title=path.stem,
            duration=float(format_data.get("duration", 0)),
            width=int(stream.get("width", 1920)),
            height=int(stream.get("height", 1080)),
            fps=fps,
            codec=stream.get("codec_name", "h264"),
        )
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError, KeyError):
        return None


def extract_frame(
    video_path: Path,
    output_path: Path,
    timestamp: float = 0.0,
    width: int = 0,
) -> bool:
    """
    Extract a single frame from video.

    Args:
        video_path: Input video path
        output_path: Output image path
        timestamp: Time to extract frame at (seconds)
        width: Optional width to scale to

    Returns:
        True if successful
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
    ]

    if width > 0:
        cmd.extend(["-vf", f"scale={width}:-1"])

    cmd.append(str(output_path))

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path.exists()
    except subprocess.CalledProcessError:
        return False


def get_video_duration(video_path: Path) -> float:
    """
    Get video duration in seconds.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds
    """
    info = _get_local_video_info(video_path)
    return info.duration if info else 0.0


def get_thumbnail_url(url: str, quality: str = "hqdefault") -> str:
    """
    Get YouTube thumbnail URL from video URL.

    Args:
        url: YouTube video URL
        quality: Thumbnail quality (maxres, hqdefault, mqdefault, default)

    Returns:
        Thumbnail URL
    """
    import re

    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    if match:
        video_id = match.group(1)
        return f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    return ""
