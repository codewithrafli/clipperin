"""Settings API routes."""

from fastapi import APIRouter, HTTPException

from clipper_ui.schemas.job import (
    SettingsUpdate,
    AIProvider,
    AIFeature,
    CaptionStyle as CaptionStyleResponse,
)
from clipper_ui.api.jobs import _settings, get_settings

router = APIRouter(prefix="/api", tags=["settings"])


# Initialize default settings
if not _settings:
    _settings.update({
        "ai_provider": "groq",
        "gemini_api_key": None,
        "groq_api_key": None,
        "openai_api_key": None,
        "enable_auto_hook": False,
        "enable_smart_reframe": False,
        "enable_dynamic_layout": False,
        "enable_progress_bar": True,
        "progress_bar_color": "#FF0050",
        "output_aspect_ratio": "9:16",
    })


@router.get("/ai-providers")
async def get_ai_providers():
    """Get available AI providers."""
    settings = get_settings()

    providers = [
        AIProvider(
            id="none",
            name="Rule-based",
            configured=True,
            cost_per_video="FREE",
            recommended=False,
        ),
        AIProvider(
            id="gemini",
            name="Google Gemini",
            configured=bool(settings.get("gemini_api_key")),
            cost_per_video="FREE",
            free_credit="Unlimited",
            signup_url="https://aistudio.google.com/app/apikey",
            recommended=False,
        ),
        AIProvider(
            id="groq",
            name="Groq",
            configured=bool(settings.get("groq_api_key")),
            cost_per_video="~Rp 40",
            free_credit="$10 credit",
            signup_url="https://console.groq.com",
            recommended=True,
        ),
        AIProvider(
            id="openai",
            name="OpenAI",
            configured=bool(settings.get("openai_api_key")),
            cost_per_video="~Rp 650",
            signup_url="https://platform.openai.com/api-keys",
            recommended=False,
        ),
    ]

    return {
        "providers": providers,
        "current_provider": settings.get("ai_provider", "none"),
    }


@router.get("/ai-features")
async def get_ai_features():
    """Get AI features status."""
    settings = get_settings()

    return {
        "features": [
            AIFeature(
                id="auto_hook",
                name="Auto Hook",
                enabled=settings.get("enable_auto_hook", False),
                description="Generate viral intro text overlay",
            ),
            AIFeature(
                id="smart_reframe",
                name="Smart Reframe",
                enabled=settings.get("enable_smart_reframe", False),
                description="Track speaker face, keep centered",
            ),
            AIFeature(
                id="dynamic_layout",
                name="Dynamic Layout",
                enabled=settings.get("enable_dynamic_layout", False),
                description="Switch Single/Split view dynamically",
            ),
        ]
    }


@router.get("/caption-styles")
async def get_caption_styles():
    """Get available caption styles."""
    from clipper_core.models.config import CaptionStyle

    styles = [
        CaptionStyleResponse(id=s.id, name=s.name)
        for s in CaptionStyle.get_default_styles()
    ]

    return {"styles": styles}


@router.get("/settings")
async def get_settings_api():
    """Get current settings."""
    settings = get_settings()

    # Don't expose full API keys
    safe_settings = settings.copy()
    for key in ["gemini_api_key", "groq_api_key", "openai_api_key"]:
        if safe_settings.get(key):
            safe_settings[key] = "***"

    return safe_settings


@router.post("/settings")
async def update_settings(request: SettingsUpdate):
    """Update settings."""
    settings = get_settings()

    # Update provider
    settings["ai_provider"] = request.ai_provider

    # Update API keys if provided
    if request.gemini_api_key:
        settings["gemini_api_key"] = request.gemini_api_key
    if request.groq_api_key:
        settings["groq_api_key"] = request.groq_api_key
    if request.openai_api_key:
        settings["openai_api_key"] = request.openai_api_key

    # Update features
    settings["enable_auto_hook"] = request.enable_auto_hook
    settings["enable_smart_reframe"] = request.enable_smart_reframe
    settings["enable_dynamic_layout"] = request.enable_dynamic_layout
    settings["enable_progress_bar"] = request.enable_progress_bar
    settings["progress_bar_color"] = request.progress_bar_color
    settings["output_aspect_ratio"] = request.output_aspect_ratio

    return {"updated": True}
