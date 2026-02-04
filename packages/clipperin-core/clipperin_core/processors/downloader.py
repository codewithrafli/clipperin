"""Video downloader using yt-dlp."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from clipperin_core.utils.video import get_video_info, VideoInfo


class VideoDownloader:
    """
    Download videos from YouTube and other platforms.

    Uses yt-dlp for broad platform support.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(tempfile.gettempdir())

    def download(
        self,
        url: str,
        output_path: Optional[Path] = None,
        quality: str = "best",
        progress_callback: Optional[callable] = None,
    ) -> Path:
        """
        Download a video from the given URL.

        Args:
            url: Video URL to download
            output_path: Optional custom output path
            quality: Video quality preset (best, good, medium)
            progress_callback: Optional callback for download progress

        Returns:
            Path to the downloaded video file
        """
        output_path = output_path or self.output_dir / "%(id)s.%(ext)s"

        cmd = [
            "yt-dlp",
            "-f", self._get_format(quality),
            "-o", str(output_path),
            "--no-playlist",
            "--progress",
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            # Parse output to find the actual file path
            for line in result.stderr.split("\n"):
                if "[download] Destination:" in line:
                    extracted_path = line.split(": ", 1)[1].strip()
                    return Path(extracted_path)

            # Fallback: try to find by video ID
            info = self.get_info(url)
            if info:
                return self.output_dir / f"{info.id}.mp4"

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Download failed: {e.stderr}") from e

        raise RuntimeError("Could not determine downloaded file path")

    def _get_format(self, quality: str) -> str:
        """Get yt-dlp format string for quality preset."""
        formats = {
            "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "good": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "medium": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "low": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        }
        return formats.get(quality, formats["good"])

    def get_info(self, url: str) -> Optional[VideoInfo]:
        """
        Get video information without downloading.

        Args:
            url: Video URL to query

        Returns:
            VideoInfo object with metadata
        """
        return get_video_info(url)

    def download_audio(
        self,
        url: str,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Download only the audio track from a video.

        Args:
            url: Video URL
            output_path: Optional custom output path

        Returns:
            Path to the downloaded audio file
        """
        output_path = output_path or self.output_dir / "%(id)s.%(ext)s"

        cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "-o", str(output_path),
            "--extract-audio",
            "--audio-format", "mp3",
            "--no-playlist",
            url,
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse output for file path
            info = self.get_info(url)
            if info:
                return self.output_dir / f"{info.id}.mp3"

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Audio download failed: {e.stderr}") from e

        raise RuntimeError("Could not determine downloaded audio path")

    def is_available(self) -> bool:
        """Check if yt-dlp is available."""
        try:
            subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
