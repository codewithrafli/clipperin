"""API routes."""

from clipper_ui.api.jobs import router as jobs_router
from clipper_ui.api.settings import router as settings_router
from clipper_ui.api.assets import router as assets_router

__all__ = ["jobs_router", "settings_router", "assets_router"]
