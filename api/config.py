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
    
    class Config:
        env_file = ".env"


settings = Settings()
