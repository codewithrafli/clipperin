import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    data_dir: str = "/data"
    
    # Whisper settings
    whisper_model: str = "base"
    whisper_language: Optional[str] = None  # None = auto-detect, or set to "en", "id", etc.
    
    # Video output settings
    output_width: int = 1080
    output_height: int = 1920
    output_fps: int = 25
    output_crf: int = 23
    
    # Clip settings
    clip_start: int = 30  # seconds
    clip_duration: int = 30  # seconds

    # AI API settings (optional - for enhanced smart detection)
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Chapter analysis settings
    enable_two_phase_flow: bool = True  # Enable chapter selection UI
    min_chapter_duration: int = 120  # 2 minutes minimum
    max_chapter_duration: int = 300  # 5 minutes maximum

    # Translation settings
    enable_translation: bool = False
    target_language: str = "id"  # "id", "zh", "ja", "ko", etc.
    translation_batch_size: int = 20  # Subtitles per API call (saves 95% API costs)

    # Output settings
    enable_multi_output: bool = True  # Generate multiple formats (raw, subtitled, SRT)
    enable_social_content: bool = False  # Generate social media content
    
    class Config:
        env_file = ".env"


settings = Settings()
