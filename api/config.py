import os
from pydantic_settings import BaseSettings
from typing import Optional, Literal


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

    # ===========================================
    # AI API Settings
    # ===========================================
    # Provider selection: "gemini", "groq", "openai", or "none"
    ai_provider: str = "gemini"

    # API Keys (user provides their own)
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # ===========================================
    # AI Features (NEW)
    # ===========================================
    # Auto Hook - generate viral intro text overlay
    enable_auto_hook: bool = False
    hook_duration: int = 5  # seconds to show hook
    hook_style: str = "bold"  # "bold", "minimal", "neon"

    # Smart Reframe - track speaker face
    enable_smart_reframe: bool = False
    reframe_smoothing: float = 0.15  # Camera movement smoothing (0.1-0.3)
    
    # Dynamic Layout - Segment-based layout switching
    enable_dynamic_layout: bool = False

    # ===========================================
    # Progress Bar Settings
    # ===========================================
    enable_progress_bar: bool = True
    progress_bar_color: str = "#FF0050"  # TikTok pink/red
    progress_bar_height: int = 6
    progress_bar_position: str = "bottom"  # "bottom" or "top"

    # ===========================================
    # Aspect Ratio Settings
    # ===========================================
    # Options: "9:16" (TikTok/Reels), "1:1" (IG Square), "4:5" (IG/FB)
    output_aspect_ratio: str = "9:16"

    # ===========================================
    # Cost Tracking (IDR)
    # ===========================================
    # Approximate costs per feature (in IDR)
    cost_hook_gemini: int = 0  # FREE tier
    cost_hook_groq: int = 15  # ~$0.001 = Rp15
    cost_hook_openai: int = 250  # ~$0.015 = Rp250
    cost_reframe: int = 0  # FREE (OpenCV local)
    cost_transcribe: int = 0  # FREE (Whisper local)

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

    def load_dynamic_settings(self):
        """Load settings from data/settings.json"""
        import json
        
        settings_path = os.path.join(self.data_dir, "settings.json")
        if not os.path.exists(settings_path):
            return

        try:
            with open(settings_path, "r") as f:
                data = json.load(f)
            
            # Update fields if they exist in data
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            print(f"✅ Loaded dynamic settings from {settings_path}")
        except Exception as e:
            print(f"❌ Failed to load settings: {e}")

    def save_dynamic_settings(self, new_settings: dict):
        """Save settings to data/settings.json and update instance"""
        import json
        
        # Update instance first
        for key, value in new_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Save to disk
        settings_path = os.path.join(self.data_dir, "settings.json")
        
        # We only save fields that are safe to persist dynamically
        # (Exclude API keys if we don't want them in cleartext JSON, but user asked for runtime updates)
        # For this local app, saving everything relevant is fine.
        
        # Re-construct export data from current state (or just the new_settings? Better to save full state of dynamic fields)
        # But to be safe, let's just save what was passed + existing dynamic values if we track them.
        # Simpler: Read existing JSON, update with new, write back.
        
        current_data = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    current_data = json.load(f)
            except:
                pass
        
        current_data.update(new_settings)
        
        try:
            with open(settings_path, "w") as f:
                json.dump(current_data, f, indent=2)
            print(f"✅ Saved settings to {settings_path}")
        except Exception as e:
            print(f"❌ Failed to save settings: {e}")


settings = Settings()
# Try loading dynamic settings on startup
settings.load_dynamic_settings()
