"""
Auto Clipper Core

Pure Python library for video clipping automation.
No CLI, no UI - just the core logic.
"""

from clipperin_core.models.job import Job, JobStatus, Chapter, Clip
from clipperin_core.models.config import Config, WhisperConfig, AIProvider, OutputConfig, CaptionStyle
from clipperin_core.pipeline.base import Pipeline, PipelineResult
from clipperin_core.pipeline.stages.download import DownloadStage
from clipperin_core.pipeline.stages.transcribe import TranscribeStage
from clipperin_core.pipeline.stages.analyze import AnalyzeStage
from clipperin_core.pipeline.stages.render import RenderStage
from clipperin_core.processors.downloader import VideoDownloader
from clipperin_core.processors.transcriber import AudioTranscriber
from clipperin_core.processors.analyzer import ContentAnalyzer
from clipperin_core.processors.renderer import VideoRenderer
from clipperin_core.processors.caption import CaptionRenderer
from clipperin_core.ai.base import AIClient, AIResponse
from clipperin_core.ai.gemini import GeminiClient
from clipperin_core.ai.groq import GroqClient
from clipperin_core.ai.openai import OpenAIClient

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
