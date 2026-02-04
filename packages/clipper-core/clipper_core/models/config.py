"""Configuration models for Auto Clipper Core."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class WhisperModel(str, Enum):
    """Available Whisper model sizes."""

    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class AIProviderType(str, Enum):
    """Available AI providers."""

    NONE = "none"
    GEMINI = "gemini"
    GROQ = "groq"
    OPENAI = "openai"


class AspectRatio(str, Enum):
    """Output aspect ratios."""

    PORTRAIT = "9:16"  # TikTok, Reels
    SQUARE = "1:1"  # Instagram
    VERTICAL = "4:5"  # Instagram, Facebook


@dataclass
class WhisperConfig:
    """Configuration for Whisper transcription."""

    model: WhisperModel = WhisperModel.BASE
    language: Optional[str] = None  # Auto-detect if None
    device: str = "cpu"  # cpu or cuda

    @property
    def model_size(self) -> str:
        """Get model size string."""
        return self.model.value


@dataclass
class AIProvider:
    """AI provider configuration."""

    provider: AIProviderType = AIProviderType.GROQ
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    model: Optional[str] = None  # Override default model

    def get_api_key(self) -> Optional[str]:
        """Get the API key for the current provider."""
        match self.provider:
            case AIProviderType.GEMINI:
                return self.gemini_api_key
            case AIProviderType.GROQ:
                return self.groq_api_key
            case AIProviderType.OPENAI:
                return self.openai_api_key
            case _:
                return None

    def get_model(self) -> str:
        """Get the model name for the current provider."""
        if self.model:
            return self.model
        match self.provider:
            case AIProviderType.GEMINI:
                return "gemini-1.5-flash"
            case AIProviderType.GROQ:
                return "llama-3.3-70b-versatile"
            case AIProviderType.OPENAI:
                return "gpt-4o-mini"
            case _:
                return "rule-based"

    @property
    def is_configured(self) -> bool:
        """Check if the current provider has an API key."""
        return bool(self.get_api_key()) if self.provider != AIProviderType.NONE else True


@dataclass
class OutputConfig:
    """Configuration for video output."""

    width: int = 1080
    height: int = 1920
    fps: int = 25
    crf: int = 23  # Quality (lower = better, larger file)
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT

    # Progress bar
    enable_progress_bar: bool = True
    progress_bar_color: str = "#FF0050"
    progress_bar_height: int = 6
    progress_bar_position: str = "bottom"

    # Hook
    enable_hook: bool = False
    hook_duration: float = 3.0
    hook_style: str = "bold"

    # Smart reframe
    enable_smart_reframe: bool = False
    reframe_smoothing: float = 0.15

    # Dynamic layout
    enable_dynamic_layout: bool = False

    @property
    def dimensions(self) -> tuple[int, int]:
        """Get output dimensions as (width, height)."""
        match self.aspect_ratio:
            case AspectRatio.PORTRAIT:
                return (1080, 1920)
            case AspectRatio.SQUARE:
                return (1080, 1080)
            case AspectRatio.VERTICAL:
                return (1080, 1350)
            case _:
                return (self.width, self.height)


@dataclass
class CaptionStyle:
    """Caption style configuration."""

    id: str
    name: str
    font_name: str = "Arial"
    font_size: int = 48
    font_color: str = "white"
    background_color: str = "black@0.5"
    outline: int = 2
    outline_color: str = "black"
    position: str = "bottom"  # top, middle, bottom
    max_width: int = 90  # Percentage of video width
    animation: str = "word"  # word, pop, typewriter, none

    # Predefined styles
    @classmethod
    def get_default_styles(cls) -> list["CaptionStyle"]:
        """Get list of default caption styles."""
        return [
            cls(
                id="default",
                name="Default",
                font_name="Arial",
                font_size=48,
                font_color="white",
            ),
            cls(
                id="karaoke",
                name="Karaoke",
                font_name="Arial Black",
                font_size=52,
                font_color="yellow",
                outline=3,
                animation="pop",
            ),
            cls(
                id="minimal",
                name="Minimal",
                font_name="Helvetica",
                font_size=42,
                font_color="white",
                outline=0,
                background_color="",
            ),
            cls(
                id="bold",
                name="Bold",
                font_name="Arial Black",
                font_size=50,
                font_color="white",
                outline=3,
            ),
            cls(
                id="neon",
                name="Neon",
                font_name="Arial",
                font_size=48,
                font_color="#00FFFF",
                outline=2,
                outline_color="#FF00FF",
            ),
            cls(
                id="tiktok",
                name="TikTok",
                font_name="Arial Black",
                font_size=52,
                font_color="yellow",
                background_color="black@0.7",
                outline=2,
            ),
            cls(
                id="typewriter",
                name="Typewriter",
                font_name="Courier New",
                font_size=44,
                font_color="white",
                animation="typewriter",
            ),
        ]


@dataclass
class Config:
    """Main configuration for Auto Clipper."""

    # Paths
    data_dir: Path = field(default_factory=lambda: Path("/data"))
    jobs_dir: Path = field(default_factory=lambda: Path("/data/jobs"))
    temp_dir: Path = field(default_factory=lambda: Path("/data/temp"))

    # Sub-configurations
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    ai: AIProvider = field(default_factory=AIProvider)
    output: OutputConfig = field(default_factory=OutputConfig)

    # Caption styles
    caption_styles: list[CaptionStyle] = field(
        default_factory=lambda: CaptionStyle.get_default_styles()
    )

    # Redis (for distributed processing)
    redis_url: str = "redis://localhost:6379/0"

    def get_job_dir(self, job_id: str) -> Path:
        """Get directory for a specific job."""
        return self.jobs_dir / job_id

    def create_job_dir(self, job_id: str) -> Path:
        """Create and return directory for a specific job."""
        job_dir = self.get_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir
