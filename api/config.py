import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    data_dir: str = "/data"
    
    # Whisper settings
    whisper_model: str = "base"
    
    # Video output settings
    output_width: int = 1080
    output_height: int = 1920
    output_fps: int = 25
    output_crf: int = 23
    
    # Clip settings
    clip_start: int = 30  # seconds
    clip_duration: int = 30  # seconds
    
    class Config:
        env_file = ".env"


settings = Settings()
