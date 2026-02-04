"""Pipeline orchestration for video processing."""

from clipper_core.pipeline.base import Pipeline, PipelineResult, PipelineStage
from clipper_core.pipeline.stages.download import DownloadStage
from clipper_core.pipeline.stages.transcribe import TranscribeStage
from clipper_core.pipeline.stages.analyze import AnalyzeStage
from clipper_core.pipeline.stages.render import RenderStage

__all__ = [
    "Pipeline",
    "PipelineResult",
    "PipelineStage",
    "DownloadStage",
    "TranscribeStage",
    "AnalyzeStage",
    "RenderStage",
]
