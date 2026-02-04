"""Time and timestamp utilities."""

import re
from typing import Union


def format_duration(seconds: float) -> str:
    """
    Format seconds as human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1:23", "1:23:45")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_timestamp(
    seconds: float,
    format: str = "srt",
) -> str:
    """
    Format seconds as timestamp.

    Args:
        seconds: Time in seconds
        format: Format type ('srt', 'ass', 'standard')

    Returns:
        Formatted timestamp

    Examples:
        >>> format_timestamp(90.5, 'srt')
        '00:01:30,500'
        >>> format_timestamp(90.5, 'ass')
        '0:01:30.50'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    centis = int((seconds % 1) * 100)

    match format:
        case "srt":
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        case "ass":
            return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"
        case "standard":
            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"
            return f"{minutes}:{secs:02d}"
        case _:
            return str(seconds)


def parse_timestamp(timestamp: str) -> float:
    """
    Parse timestamp string to seconds.

    Args:
        timestamp: Timestamp in various formats

    Returns:
        Time in seconds

    Examples:
        >>> parse_timestamp("1:30")
        90.0
        >>> parse_timestamp("1:30.5")
        90.5
        >>> parse_timestamp("00:01:30,500")
        90.5
    """
    # Try SRT format: HH:MM:SS,mmm
    srt_match = re.match(r"(\d+):(\d+):(\d+),(\d+)", timestamp)
    if srt_match:
        h, m, s, ms = map(int, srt_match.groups())
        return h * 3600 + m * 60 + s + ms / 1000

    # Try standard format: HH:MM:SS.mmm or MM:SS.mmm
    parts = timestamp.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)

    # Try plain number
    try:
        return float(timestamp)
    except ValueError:
        return 0.0


def seconds_to_samples(seconds: float, sample_rate: int) -> int:
    """Convert seconds to audio samples."""
    return int(seconds * sample_rate)


def samples_to_seconds(samples: int, sample_rate: int) -> float:
    """Convert audio samples to seconds."""
    return samples / sample_rate if sample_rate > 0 else 0.0


def frame_to_time(frame: int, fps: float) -> float:
    """Convert frame number to time in seconds."""
    return frame / fps if fps > 0 else 0.0


def time_to_frame(time: float, fps: float) -> int:
    """Convert time in seconds to frame number."""
    return int(time * fps) if fps > 0 else 0


def time_range(start: float, end: float, step: float = 1.0):
    """
    Generate time values in a range.

    Args:
        start: Start time in seconds
        end: End time in seconds
        step: Step size in seconds

    Yields:
        Time values in the range
    """
    current = start
    while current < end:
        yield current
        current += step


def clamp_time(seconds: float, max_duration: float) -> float:
    """Clamp time to valid range."""
    return max(0.0, min(seconds, max_duration))
