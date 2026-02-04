"""Tests for clipperin-core processors."""

import pytest
from pathlib import Path
from clipperin_core.processors.caption import CaptionRenderer
from clipperin_core.models.config import CaptionStyle


def test_caption_style_defaults():
    """Test default caption styles are available."""
    styles = CaptionStyle.get_default_styles()
    assert len(styles) >= 7
    assert any(s.id == "default" for s in styles)
    assert any(s.id == "karaoke" for s in styles)


def test_caption_renderer():
    """Test caption renderer initialization."""
    renderer = CaptionRenderer()
    assert renderer.default_style is not None
    assert renderer.default_style.id == "default"


def test_format_srt_time():
    """Test SRT timestamp formatting."""
    renderer = CaptionRenderer()
    assert renderer._seconds_to_srt_time(90.5) == "00:01:30,500"
    assert renderer._seconds_to_srt_time(3661.0) == "01:01:01,000"


def test_word_level_segments():
    """Test word-level segmentation."""
    words = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 0.5, "end": 1.0},
    ]
    renderer = CaptionRenderer()
    segments = renderer.word_level_segments(words)
    assert len(segments) == 1
    assert segments[0]["text"] == "Hello world"
