"""Pipeline orchestration for video processing."""

from clipperin_core.pipeline.base import Pipeline, PipelineResult, PipelineStage
from clipperin_core.pipeline.stages.download import DownloadStage
from clipperin_core.pipeline.stages.transcribe import TranscribeStage
from clipperin_core.pipeline.stages.analyze import AnalyzeStage
from clipperin_core.pipeline.stages.render import RenderStage

__all__ = [
    "Pipeline",
    "PipelineResult",
    "PipelineStage",
    "DownloadStage",
    "TranscribeStage",
    "AnalyzeStage",
    "RenderStage",
]
