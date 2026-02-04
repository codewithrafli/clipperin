"""User settings management."""

import json
from pathlib import Path

from clipperin_core import Config, WhisperModel, AIProvider


def get_config_path() -> Path:
    """Get user config file path."""
    config_dir = Path.home() / ".clipper"
    return config_dir / "config.json"


def get_default_config() -> Config:
    """Get default configuration."""
    return Config()


def load_user_config() -> Config:
    """
    Load user configuration from file.

    Returns:
        Config object (default if file doesn't exist)
    """
    config_path = get_config_path()

    if not config_path.exists():
        return get_default_config()

    with open(config_path) as f:
        data = json.load(f)

    config = get_default_config()

    # Apply saved values
    if "whisper" in data:
        w = data["whisper"]
        if "model" in w:
            config.whisper.model = WhisperModel(w["model"])
        if "language" in w:
            config.whisper.language = w.get("language")
        if "device" in w:
            config.whisper.device = w["device"]

    if "ai" in data:
        a = data["ai"]
        if "provider" in a:
            config.ai.provider = AIProvider(a["provider"])
        if "gemini_api_key" in a:
            config.ai.gemini_api_key = a.get("gemini_api_key")
        if "groq_api_key" in a:
            config.ai.groq_api_key = a.get("groq_api_key")
        if "openai_api_key" in a:
            config.ai.openai_api_key = a.get("openai_api_key")

    if "output" in data:
        o = data["output"]
        if "aspect_ratio" in o:
            config.output.aspect_ratio = o["aspect_ratio"]
        if "enable_progress_bar" in o:
            config.output.enable_progress_bar = o["enable_progress_bar"]
        if "progress_bar_color" in o:
            config.output.progress_bar_color = o["progress_bar_color"]
        if "enable_hook" in o:
            config.output.enable_hook = o["enable_hook"]
        if "enable_smart_reframe" in o:
            config.output.enable_smart_reframe = o["enable_smart_reframe"]

    if "data_dir" in data:
        config.data_dir = Path(data["data_dir"])
    if "jobs_dir" in data:
        config.jobs_dir = Path(data["jobs_dir"])

    return config


def save_user_config(config: Config) -> None:
    """
    Save user configuration to file.

    Args:
        config: Config object to save
    """
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "whisper": {
            "model": config.whisper.model.value,
            "language": config.whisper.language,
            "device": config.whisper.device,
        },
        "ai": {
            "provider": config.ai.provider.value,
            "gemini_api_key": config.ai.gemini_api_key,
            "groq_api_key": config.ai.groq_api_key,
            "openai_api_key": config.ai.openai_api_key,
        },
        "output": {
            "aspect_ratio": config.output.aspect_ratio.value,
            "enable_progress_bar": config.output.enable_progress_bar,
            "progress_bar_color": config.output.progress_bar_color,
            "enable_hook": config.output.enable_hook,
            "enable_smart_reframe": config.output.enable_smart_reframe,
        },
        "data_dir": str(config.data_dir),
        "jobs_dir": str(config.jobs_dir),
    }

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
