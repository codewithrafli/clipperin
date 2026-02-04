"""Job schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    """Job status enum."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    CHAPTERS_READY = "chapters_ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreate(BaseModel):
    """Request to create a new job."""

    url: str = Field(..., description="Video URL to process")
    caption_style: str = Field("default", description="Caption style ID")
    auto_detect: bool = Field(True, description="Auto-detect chapters")
    use_ai_detection: bool = Field(False, description="Use AI for chapter detection")
    enable_auto_hook: bool = Field(False, description="Enable viral hook overlay")
    enable_smart_reframe: bool = Field(False, description="Enable smart face reframe")
    enable_dynamic_layout: bool = Field(False, description="Enable dynamic layout")


class ChapterResponse(BaseModel):
    """Chapter response."""

    id: str
    title: str
    start: float
    end: float
    duration: float
    summary: Optional[str] = None
    confidence: float = 1.0
    hooks: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ClipResponse(BaseModel):
    """Clip response."""

    filename: str
    title: str
    start: float
    end: float
    duration: float
    thumbnail: Optional[str] = None
    score: int = 75

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    """Job response."""

    id: str
    url: str
    status: JobStatus
    progress: float = 0.0
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None
    chapters: List[ChapterResponse] = Field(default_factory=list)
    clips: List[ClipResponse] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ChapterSelectRequest(BaseModel):
    """Request to select chapters for rendering."""

    chapter_ids: List[str] = Field(..., description="Chapter IDs to render")
    options: dict = Field(default_factory=dict, description="Rendering options")


class SettingsUpdate(BaseModel):
    """Settings update request."""

    ai_provider: str = Field("none", description="AI provider: none, gemini, groq, openai")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API key")
    groq_api_key: Optional[str] = Field(None, description="Groq API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    enable_auto_hook: bool = Field(False, description="Enable auto hook")
    enable_smart_reframe: bool = Field(False, description="Enable smart reframe")
    enable_dynamic_layout: bool = Field(False, description="Enable dynamic layout")
    enable_progress_bar: bool = Field(True, description="Enable progress bar")
    progress_bar_color: str = Field("#FF0050", description="Progress bar color")
    output_aspect_ratio: str = Field("9:16", description="Aspect ratio: 9:16, 1:1, 4:5")


class AIProvider(BaseModel):
    """AI provider info."""

    id: str
    name: str
    configured: bool
    cost_per_video: str
    free_credit: Optional[str] = None
    signup_url: Optional[str] = None
    recommended: bool = False


class AIFeature(BaseModel):
    """AI feature info."""

    id: str
    name: str
    enabled: bool
    description: str


class CaptionStyle(BaseModel):
    """Caption style info."""

    id: str
    name: str
