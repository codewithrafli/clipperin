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
from tasks import celery_app, process_video, CAPTION_STYLES

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


class JobCreate(BaseModel):
    url: str
    clip_start: Optional[int] = None
    clip_duration: Optional[int] = None
    caption_style: Optional[str] = "default"
    auto_detect: Optional[bool] = True
    use_ai_detection: Optional[bool] = False


class JobResponse(BaseModel):
    id: str
    url: str
    status: str
    progress: int
    created_at: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    clips: Optional[list] = []


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
    
    # Start Celery task
    options = {
        "caption_style": job.caption_style,
        "auto_detect": job.auto_detect,
        "use_ai_detection": job.use_ai_detection
    }
    if job.clip_start is not None:
        options["clip_start"] = job.clip_start
    if job.clip_duration is not None:
        options["clip_duration"] = job.clip_duration
    
    task = process_video.delay(job_id, job.url, options)
    
    # Store job info
    jobs_db[job_id] = {
        "id": job_id,
        "url": job.url,
        "task_id": task.id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "eta_seconds": None,
        "error": None
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
        job["progress"] = result.info.get("progress", 10)
    elif result.state == "TRANSCRIBING":
        job["status"] = "transcribing"
        job["progress"] = result.info.get("progress", 40)
    elif result.state == "PROCESSING":
        job["status"] = "processing"
        job["progress"] = result.info.get("progress", 70)
    elif result.state == "COMPLETED" or result.state == "SUCCESS":
        job["status"] = "completed"
        job["progress"] = 100
        # Add clips to job info
        if isinstance(result.result, dict):
            job["clips"] = result.result.get("clips", [])
    elif result.state == "FAILED" or result.state == "FAILURE":
        job["status"] = "failed"
        job["error"] = str(result.info) if result.info else "Unknown error"
    # Set ETA based on current step (rough estimates)
    # Whisper doesn't provide real-time progress, so use step-based ETA
    eta_map = {
        "pending": 300,      # 5 min estimate
        "downloading": 120,  # 2 min for download
        "transcribing": 300, # 5 min for transcription (varies by video length)
        "processing": 60,    # 1 min for ffmpeg
    }
    job["eta_seconds"] = eta_map.get(job["status"])
