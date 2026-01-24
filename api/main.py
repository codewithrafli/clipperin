import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery.result import AsyncResult

from config import settings
from tasks import (
    celery_app,
    process_video,
    process_video_phase1,
    process_selected_chapters,
    CAPTION_STYLES
)

app = FastAPI(
    title="Auto Clipper Engine",
    description="Self-hosted video clipping API - No recurring fees!",
    version="1.0.0"
)

# CORS for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job storage (for simplicity - could use Redis/SQLite)
jobs_db = {}


def load_jobs_from_disk():
    """Recover jobs from disk on startup"""
    jobs_dir = os.path.join(settings.data_dir, "jobs")
    if not os.path.exists(jobs_dir):
        return

    print(f"🔄 Recovering jobs from {jobs_dir}...")
    
    for job_id in os.listdir(jobs_dir):
        job_path = os.path.join(jobs_dir, job_id)
        if not os.path.isdir(job_path):
            continue
            
        # skip if already loaded
        if job_id in jobs_db:
            continue

        try:
            # Try to reconstruct state from files
            job_state = {
                "id": job_id,
                "url": "Unknown URL",
                "status": "failed", # Default fallback
                "progress": 0,
                "created_at": datetime.fromtimestamp(os.path.getctime(job_path)).isoformat(),
                "task_id": None, # Cannot recover task ID easily without persistence
                "clips": [],
                "chapters": [],
                "selected_chapters": [],
                "error": None
            }

            # 1. Look for metadata.json (created by Phase 1)
            metadata_file = os.path.join(job_path, "metadata.json")
            if os.path.exists(metadata_file):
                import json
                with open(metadata_file, "r") as f:
                     meta = json.load(f)
                     # If we have metadata, we at least finished Phase 1 semi-successfully
                     # but we need to check chapters.json
            
            # 2. Check status based on files
            clips_file = os.path.join(job_path, "clips.json")
            chapters_file = os.path.join(job_path, "chapters.json")
            
            if os.path.exists(clips_file):
                job_state["status"] = "completed"
                job_state["progress"] = 100
                import json
                with open(clips_file, "r") as f:
                    job_state["clips"] = json.load(f)
            elif os.path.exists(chapters_file):
                 job_state["status"] = "chapters_ready"
                 job_state["progress"] = 60
                 import json
                 with open(chapters_file, "r") as f:
                    job_state["chapters"] = json.load(f)
            
            # 3. Recover URL from logs
            log_file = os.path.join(job_path, "progress.log")
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                     content = f.read()
                     # Look for URL pattern
                     import re
                     url_match = re.search(r"📎 URL: (https?://[^\s]+)", content)
                     if url_match:
                         job_state["url"] = url_match.group(1)
            
            jobs_db[job_id] = job_state
            print(f"   ✅ Loaded job {job_id} ({job_state['status']})")
            
        except Exception as e:
            print(f"   ❌ Failed to load job {job_id}: {e}")

@app.on_event("startup")
async def startup_event():
    load_jobs_from_disk()



class JobCreate(BaseModel):
    url: str
    clip_start: Optional[int] = None
    clip_duration: Optional[int] = None
    caption_style: Optional[str] = "default"
    auto_detect: Optional[bool] = True
    use_ai_detection: Optional[bool] = False
    # New options for two-phase flow
    enable_translation: Optional[bool] = None  # Use settings default if None
    enable_multi_output: Optional[bool] = None
    enable_social_content: Optional[bool] = None


class ChapterSelection(BaseModel):
    chapter_ids: list[str]  # e.g., ["ch_1", "ch_3"]
    options: Optional[dict] = {}


class JobResponse(BaseModel):
    id: str
    url: str
    status: str
    progress: int
    created_at: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    clips: Optional[list] = []
    chapters: Optional[list] = []  # NEW: Available chapters for selection
    selected_chapters: Optional[list] = []  # NEW: User-selected chapter IDs


@app.get("/")
def root():
    return {
        "name": "Auto Clipper Engine",
        "version": "1.0.0",
        "message": "No recurring API fees - 100% offline processing!"
    }


@app.get("/api/detection-modes")
def get_detection_modes():
    """Get available detection modes"""
    gemini_available = bool(settings.gemini_api_key)
    openai_available = bool(settings.openai_api_key)
    ai_available = gemini_available or openai_available
    
    return {
        "modes": [
            {
                "id": "rule-based",
                "name": "Rule-based (Free)",
                "description": "Keyword analysis, no API needed",
                "available": True
            },
            {
                "id": "ai",
                "name": "AI-Powered",
                "description": "Gemini/OpenAI for better accuracy",
                "available": ai_available,
                "provider": "gemini" if gemini_available else ("openai" if openai_available else None)
            }
        ],
        "ai_configured": ai_available
    }


@app.post("/api/jobs", response_model=JobResponse)
def create_job(job: JobCreate):
    """Submit a new video clipping job"""
    job_id = str(uuid.uuid4())[:8]

    # Build options
    options = {
        "caption_style": job.caption_style,
        "auto_detect": job.auto_detect,
        "use_ai_detection": job.use_ai_detection,
        "enable_translation": job.enable_translation if job.enable_translation is not None else settings.enable_translation,
        "enable_multi_output": job.enable_multi_output if job.enable_multi_output is not None else settings.enable_multi_output,
        "enable_social_content": job.enable_social_content if job.enable_social_content is not None else settings.enable_social_content,
    }
    if job.clip_start is not None:
        options["clip_start"] = job.clip_start
    if job.clip_duration is not None:
        options["clip_duration"] = job.clip_duration

    # Use two-phase flow if enabled (chapter selection)
    if settings.enable_two_phase_flow and job.auto_detect:
        task = process_video_phase1.delay(job_id, job.url, options)
        flow_type = "two_phase"
    else:
        # Legacy single-phase flow
        task = process_video.delay(job_id, job.url, options)
        flow_type = "single_phase"

    # Store job info
    jobs_db[job_id] = {
        "id": job_id,
        "url": job.url,
        "task_id": task.id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "eta_seconds": None,
        "error": None,
        "clips": [],
        "chapters": [],
        "selected_chapters": [],
        "flow_type": flow_type,
        "options": options
    }

    return JobResponse(**jobs_db[job_id])


@app.get("/api/jobs", response_model=list[JobResponse])
def list_jobs():
    """List all jobs"""
    # Update status from Celery
    for job_id, job in jobs_db.items():
        update_job_status(job_id)
    
    return [JobResponse(**job) for job in jobs_db.values()]


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    """Get job status"""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_job_status(job_id)
    return JobResponse(**jobs_db[job_id])


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str, filename: str = "output.mp4"):
    """Download completed video"""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    update_job_status(job_id)
    job = jobs_db[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job not ready. Status: {job['status']}")

    file_path = os.path.join(settings.data_dir, "jobs", job_id, filename)

    if not os.path.exists(file_path):
        # Fallback for backward compatibility
        if filename == "output.mp4":
            raise HTTPException(status_code=404, detail="Video not found")
        # Try finding it in the clips list if possible?
        # For now just return 404
        raise HTTPException(status_code=404, detail=f"File {filename} not found")

    return FileResponse(file_path, media_type="video/mp4", filename=filename)


@app.get("/api/jobs/{job_id}/thumbnail/{filename}")
def get_thumbnail(job_id: str, filename: str):
    """Get thumbnail for a clip"""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    thumbnail_path = os.path.join(settings.data_dir, "jobs", job_id, filename)

    if not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(thumbnail_path, media_type="image/jpeg")


@app.get("/api/jobs/{job_id}/logs")
def get_job_logs(job_id: str):
    """Get job processing logs"""
    log_file = os.path.join(settings.data_dir, "jobs", job_id, "progress.log")
    
    if not os.path.exists(log_file):
        return {"logs": []}
    
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.read().strip().split("\n")
    
    return {"logs": lines}


@app.get("/api/caption-styles")
def get_caption_styles():
    """Get available caption styles"""
    return {
        "styles": [
            {"id": key, "name": style["name"]}
            for key, style in CAPTION_STYLES.items()
        ]
    }


@app.get("/api/jobs/{job_id}/clips")
def get_suggested_clips(job_id: str):
    """Get AI-detected suggested clips for a job"""
    clips_file = os.path.join(settings.data_dir, "jobs", job_id, "suggested_clips.json")

    if not os.path.exists(clips_file):
        return {"clips": [], "message": "No clips detected yet. Wait for transcription to complete."}

    import json
    with open(clips_file, "r") as f:
        clips = json.load(f)

    return {"clips": clips}


# =============================================================================
# CHAPTER SELECTION ENDPOINTS (New Feature)
# =============================================================================

@app.get("/api/jobs/{job_id}/chapters")
def get_chapters(job_id: str):
    """Get available chapters for selection"""
    import json

    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    update_job_status(job_id)
    job = jobs_db[job_id]

    chapters_file = os.path.join(settings.data_dir, "jobs", job_id, "chapters.json")

    if not os.path.exists(chapters_file):
        return {
            "chapters": [],
            "status": job["status"],
            "can_select": False,
            "message": "Chapters not ready yet. Wait for analysis to complete."
        }

    with open(chapters_file, "r", encoding="utf-8") as f:
        chapters = json.load(f)

    return {
        "chapters": chapters,
        "status": job["status"],
        "can_select": job["status"] == "chapters_ready"
    }


@app.post("/api/jobs/{job_id}/select-chapters")
def select_chapters(job_id: str, selection: ChapterSelection):
    """User selects which chapters to process into clips"""
    import json

    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    update_job_status(job_id)
    job = jobs_db[job_id]

    if job["status"] != "chapters_ready":
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'chapters_ready' state. Current: {job['status']}"
        )

    # Load chapters to validate selection
    chapters_file = os.path.join(settings.data_dir, "jobs", job_id, "chapters.json")
    if not os.path.exists(chapters_file):
        raise HTTPException(status_code=400, detail="No chapters available")

    with open(chapters_file, "r", encoding="utf-8") as f:
        chapters = json.load(f)

    # Validate selected chapters exist
    available_ids = {ch["id"] for ch in chapters}
    invalid_ids = set(selection.chapter_ids) - available_ids
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid chapter IDs: {list(invalid_ids)}"
        )

    if not selection.chapter_ids:
        raise HTTPException(status_code=400, detail="No chapters selected")

    # Merge selection options with job options
    options = job.get("options", {}).copy()
    options.update(selection.options or {})

    # Store selection and trigger Phase 2 processing
    job["selected_chapters"] = selection.chapter_ids
    job["status"] = "processing"

    # Start Phase 2 task
    task = process_selected_chapters.delay(
        job_id,
        selection.chapter_ids,
        options
    )
    job["task_id"] = task.id  # Update task ID to Phase 2 task

    return {
        "message": "Processing started",
        "selected": selection.chapter_ids,
        "total_selected": len(selection.chapter_ids)
    }


@app.get("/api/settings")
def get_settings():
    """Get current system settings (public subset)"""
    return {
        "enable_two_phase_flow": settings.enable_two_phase_flow,
        "enable_translation": settings.enable_translation,
        "target_language": settings.target_language,
        "enable_multi_output": settings.enable_multi_output,
        "enable_social_content": settings.enable_social_content,
        "ai_available": bool(settings.gemini_api_key or settings.openai_api_key),
        "whisper_model": settings.whisper_model
    }


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    """Delete a job and its files"""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Remove files
    job_dir = os.path.join(settings.data_dir, "jobs", job_id)
    if os.path.exists(job_dir):
        import shutil
        shutil.rmtree(job_dir)
    
    del jobs_db[job_id]
    return {"message": "Job deleted"}


def update_job_status(job_id: str):
    """Update job status from Celery task"""
    import json

    job = jobs_db.get(job_id)
    if not job:
        return

    task_id = job.get("task_id")
    if not task_id:
        return

    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        job["status"] = "pending"
        job["progress"] = 0
    elif result.state == "DOWNLOADING":
        job["status"] = "downloading"
        job["progress"] = result.info.get("progress", 10) if result.info else 10
    elif result.state == "TRANSCRIBING":
        job["status"] = "transcribing"
        job["progress"] = result.info.get("progress", 30) if result.info else 30
    elif result.state == "ANALYZING":
        job["status"] = "analyzing"
        job["progress"] = result.info.get("progress", 50) if result.info else 50
    elif result.state == "CHAPTERS_READY":
        job["status"] = "chapters_ready"
        job["progress"] = 60
        # Load chapters from result or file
        if result.info and isinstance(result.info, dict):
            job["chapters"] = result.info.get("chapters", [])
        else:
            # Try loading from file
            chapters_file = os.path.join(settings.data_dir, "jobs", job_id, "chapters.json")
            if os.path.exists(chapters_file):
                with open(chapters_file, "r", encoding="utf-8") as f:
                    job["chapters"] = json.load(f)
    elif result.state == "PROCESSING":
        job["status"] = "processing"
        info = result.info if result.info else {}
        job["progress"] = info.get("progress", 70)
        # Include current chapter info if available
        if info.get("current_chapter"):
            job["current_chapter"] = info.get("current_chapter")
            job["current_index"] = info.get("current_index", 0)
            job["total_chapters"] = info.get("total_chapters", 0)
    elif result.state == "COMPLETED" or result.state == "SUCCESS":
        # Check if the result indicates we're just ready for chapters (Phase 1 complete)
        if isinstance(result.result, dict) and result.result.get("status") == "chapters_ready":
            job["status"] = "chapters_ready"
            job["progress"] = 60
            if "chapters" in result.result:
                job["chapters"] = result.result["chapters"]
            elif "chapters" in result.info:
                 job["chapters"] = result.info.get("chapters", [])
        else:
            job["status"] = "completed"
            job["progress"] = 100
            # Add clips to job info
            if isinstance(result.result, dict):
                job["clips"] = result.result.get("clips", [])
            else:
                # Try loading from file
                clips_file = os.path.join(settings.data_dir, "jobs", job_id, "clips.json")
                if os.path.exists(clips_file):
                    with open(clips_file, "r", encoding="utf-8") as f:
                        job["clips"] = json.load(f)
    elif result.state == "FAILED" or result.state == "FAILURE":
        job["status"] = "failed"
        job["error"] = str(result.info) if result.info else "Unknown error"

    # Set ETA based on current step (rough estimates)
    eta_map = {
        "pending": 300,         # 5 min estimate
        "downloading": 120,     # 2 min for download
        "transcribing": 300,    # 5 min for transcription
        "analyzing": 60,        # 1 min for chapter analysis
        "chapters_ready": None, # Waiting for user
        "processing": 120,      # 2 min for clip generation
    }
    job["eta_seconds"] = eta_map.get(job["status"])
