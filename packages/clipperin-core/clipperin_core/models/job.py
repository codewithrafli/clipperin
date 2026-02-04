"""Domain entity models for jobs, chapters, and clips."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


class JobStatus(str, Enum):
    """Status of a clipping job."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    CHAPTERS_READY = "chapters_ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Chapter:
    """A chapter/segment detected in a video."""

    id: str
    title: str
    start: float  # Start time in seconds
    end: float  # End time in seconds
    duration: float
    summary: Optional[str] = None
    confidence: float = 1.0  # 0-1, how confident the analyzer is
    hooks: list[str] = field(default_factory=list)  # Potential viral hooks

    @property
    def start_formatted(self) -> str:
        """Format start time as MM:SS."""
        minutes = int(self.start // 60)
        seconds = int(self.start % 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def end_formatted(self) -> str:
        """Format end time as MM:SS."""
        minutes = int(self.end // 60)
        seconds = int(self.end % 60)
        return f"{minutes}:{seconds:02d}"


@dataclass
class Clip:
    """A rendered clip ready for export."""

    filename: str
    title: str
    start: float
    end: float
    duration: float
    thumbnail: Optional[str] = None
    score: int = 75  # Viral score 0-100
    srt_path: Optional[Path] = None

    @classmethod
    def from_chapter(cls, chapter: Chapter, filename: str, score: int = 75) -> "Clip":
        """Create a Clip from a Chapter."""
        return cls(
            filename=filename,
            title=chapter.title,
            start=chapter.start,
            end=chapter.end,
            duration=chapter.duration,
            score=score,
        )


@dataclass
class Job:
    """A clipping job - represents one video from source to output."""

    id: str = field(default_factory=lambda: str(uuid4()))
    url: str = ""
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0  # 0-100
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None

    # Input/output paths
    video_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    srt_path: Optional[Path] = None
    output_dir: Optional[Path] = None

    # Analysis results
    chapters: list[Chapter] = field(default_factory=list)
    clips: list[Clip] = field(default_factory=list)
    transcription: list[dict] = field(default_factory=list)

    # Job settings
    caption_style: str = "default"
    use_ai: bool = False
    enable_auto_hook: bool = False
    enable_smart_reframe: bool = False
    enable_dynamic_layout: bool = False

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_status(self, status: JobStatus, progress: float = None, error: str = None) -> None:
        """Update job status and optional progress."""
        self.status = status
        self.updated_at = datetime.utcnow()
        if progress is not None:
            self.progress = progress
        if error:
            self.error = error

    def add_chapter(self, chapter: Chapter) -> None:
        """Add a chapter to the job."""
        self.chapters.append(chapter)

    def add_clip(self, clip: Clip) -> None:
        """Add a rendered clip to the job."""
        self.clips.append(clip)

    @property
    def video_id(self) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        if "youtube.com" in self.url or "youtu.be" in self.url:
            import re
            match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", self.url)
            return match.group(1) if match else None
        return None

    @property
    def is_complete(self) -> bool:
        """Check if job is complete."""
        return self.status == JobStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == JobStatus.FAILED

    @property
    def is_processing(self) -> bool:
        """Check if job is currently processing."""
        return self.status in {
            JobStatus.DOWNLOADING,
            JobStatus.TRANSCRIBING,
            JobStatus.ANALYZING,
            JobStatus.PROCESSING,
        }
