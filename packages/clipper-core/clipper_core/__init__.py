"""
Auto Clipper Core

Pure Python library for video clipping automation.
No CLI, no UI - just the core logic.
"""

from clipper_core.models.job import Job, JobStatus, Chapter, Clip
from clipper_core.models.config import Config, WhisperConfig, AIProvider, OutputConfig, CaptionStyle
from clipper_core.pipeline.base import Pipeline, PipelineResult
from clipper_core.pipeline.stages.download import DownloadStage
from clipper_core.pipeline.stages.transcribe import TranscribeStage
from clipper_core.pipeline.stages.analyze import AnalyzeStage
from clipper_core.pipeline.stages.render import RenderStage
from clipper_core.processors.downloader import VideoDownloader
from clipper_core.processors.transcriber import AudioTranscriber
from clipper_core.processors.analyzer import ContentAnalyzer
from clipper_core.processors.renderer import VideoRenderer
from clipper_core.processors.caption import CaptionRenderer
from clipper_core.ai.base import AIClient, AIResponse
from clipper_core.ai.gemini import GeminiClient
from clipper_core.ai.groq import GroqClient
from clipper_core.ai.openai import OpenAIClient

__version__ = "0.1.0"

__all__ = [
    # Models
    "Job",
    "JobStatus",
    "Chapter",
    "Clip",
    "Config",
    "WhisperConfig",
    "AIProvider",
    "OutputConfig",
    "CaptionStyle",
    # Pipeline
    "Pipeline",
    "PipelineResult",
    "DownloadStage",
    "TranscribeStage",
    "AnalyzeStage",
    "RenderStage",
    # Processors
    "VideoDownloader",
    "AudioTranscriber",
    "ContentAnalyzer",
    "VideoRenderer",
    "CaptionRenderer",
    # AI
    "AIClient",
    "AIResponse",
    "GeminiClient",
    "GroqClient",
    "OpenAIClient",
]
