"""Static assets API routes."""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(tags=["assets"])

# Frontend build directory
frontend_dist = Path("/app/frontend/dist")


@router.get("/assets/{file_path:path}")
async def get_asset(file_path: str):
    """Serve frontend assets."""
    file = frontend_dist / "assets" / file_path
    if file.exists():
        return FileResponse(file)
    return FileResponse(frontend_dist / "index.html")


@router.get("/{_:path}")
async def catch_all(_: str):
    """Catch-all for SPA routing."""
    index = frontend_dist / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"error": "Frontend not built"}
