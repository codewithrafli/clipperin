"""Basic smoke tests for clipperin-core models."""

import pytest
from clipperin_core import Job, JobStatus, Chapter, Clip
from clipperin_core.models.config import Config, WhisperModel, AIProviderType


def test_job_creation():
    """Test basic job creation and defaults."""
    job = Job(url="https://youtube.com/watch?v=dQw4w9WgXcQ")
    assert job.id
    assert job.url == "https://youtube.com/watch?v=dQw4w9WgXcQ"
    assert job.status == JobStatus.PENDING
    assert job.progress == 0.0
    assert job.chapters == []
    assert job.clips == []


def test_job_status_update():
    """Test job status updates."""
    job = Job(url="https://youtube.com/watch?v=test")
    job.update_status(JobStatus.DOWNLOADING, progress=50)
    assert job.status == JobStatus.DOWNLOADING
    assert job.progress == 50


def test_chapter_creation():
    """Test chapter creation."""
    chapter = Chapter(
        id="test-chapter",
        title="Test Chapter",
        start=10.0,
        end=45.0,
        duration=35.0,
    )
    assert chapter.id == "test-chapter"
    assert chapter.start_formatted == "0:10"
    assert chapter.end_formatted == "0:45"
    assert chapter.duration == 35.0


def test_config_defaults():
    """Test default configuration."""
    config = Config()
    assert config.whisper.model == WhisperModel.BASE
    assert config.ai.provider == AIProviderType.GROQ
    assert config.output.aspect_ratio.value == "9:16"


def test_clip_from_chapter():
    """Test creating clip from chapter."""
    chapter = Chapter(
        id="test-chapter",
        title="Test Chapter",
        start=10.0,
        end=45.0,
        duration=35.0,
    )
    clip = Clip.from_chapter(chapter, "clip.mp4", score=85)
    assert clip.filename == "clip.mp4"
    assert clip.title == "Test Chapter"
    assert clip.start == 10.0
    assert clip.end == 45.0
    assert clip.score == 85
