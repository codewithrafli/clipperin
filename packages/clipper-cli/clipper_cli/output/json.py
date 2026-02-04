"""JSON output utilities."""

import json
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


def to_json(obj: Any, pretty: bool = True) -> str:
    """
    Convert object to JSON string.

    Args:
        obj: Object to convert
        pretty: Whether to format prettily

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(obj, indent=2, default=str)
    return json.dumps(obj, default=str)


def from_json(text: str) -> Any:
    """
    Parse JSON string.

    Args:
        text: JSON string

    Returns:
        Parsed object
    """
    return json.loads(text)


def write_json(obj: Any, path: Path, pretty: bool = True) -> None:
    """
    Write object to JSON file.

    Args:
        obj: Object to write
        path: Output file path
        pretty: Whether to format prettily
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(to_json(obj, pretty))


def read_json(path: Path) -> Any:
    """
    Read JSON file.

    Args:
        path: File path to read

    Returns:
        Parsed object
    """
    with open(path) as f:
        return from_json(f.read())


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for clipper objects."""

    def default(self, obj):
        from clipper_core.models.job import Job, Chapter, Clip, JobStatus

        if isinstance(obj, Job):
            return {
                "id": obj.id,
                "url": obj.url,
                "status": obj.status.value,
                "progress": obj.progress,
                "created_at": obj.created_at.isoformat() if obj.created_at else None,
                "video_path": str(obj.video_path) if obj.video_path else None,
                "chapters": obj.chapters,
                "clips": obj.clips,
            }

        if isinstance(obj, Chapter):
            return {
                "id": obj.id,
                "title": obj.title,
                "start": obj.start,
                "end": obj.end,
                "duration": obj.duration,
                "summary": obj.summary,
                "confidence": obj.confidence,
                "hooks": obj.hooks,
            }

        if isinstance(obj, Clip):
            return {
                "filename": obj.filename,
                "title": obj.title,
                "start": obj.start,
                "end": obj.end,
                "duration": obj.duration,
                "thumbnail": obj.thumbnail,
                "score": obj.score,
            }

        if isinstance(obj, JobStatus):
            return obj.value

        if hasattr(obj, "model_dump"):
            return obj.model_dump()

        return super().default(obj)
