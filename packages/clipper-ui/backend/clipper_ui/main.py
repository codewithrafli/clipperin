"""FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from clipper_ui.api import jobs_router, settings_router, assets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    # Startup
    import os
    os.makedirs("/data/jobs", exist_ok=True)
    yield
    # Shutdown


app = FastAPI(
    title="Auto Clipper API",
    description="Self-hosted video clipping solution",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jobs_router)
app.include_router(settings_router)
app.include_router(assets_router)

# Static files for development
try:
    from pathlib import Path
    frontend_path = Path("/app/frontend/dist")
    if frontend_path.exists():
        app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
except Exception:
    pass


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}
