"""API routes."""

from clipperin_ui.api.jobs import router as jobs_router
from clipperin_ui.api.settings import router as settings_router
from clipperin_ui.api.assets import router as assets_router

__all__ = ["jobs_router", "settings_router", "assets_router"]
