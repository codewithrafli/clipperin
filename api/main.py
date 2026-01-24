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
from tasks import celery_app, process_video

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


class JobResponse(BaseModel):
    id: str
    url: str
    status: str
    progress: int
    created_at: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None


@app.get("/")
def root():
    return {
        "name": "Auto Clipper Engine",
        "version": "1.0.0",
        "message": "No recurring API fees - 100% offline processing!"
    }


@app.post("/api/jobs", response_model=JobResponse)
def create_job(job: JobCreate):
    """Submit a new video clipping job"""
    job_id = str(uuid.uuid4())[:8]
    
    # Start Celery task
    options = {}
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
def download_job(job_id: str):
    """Download completed video"""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_job_status(job_id)
    job = jobs_db[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job not ready. Status: {job['status']}")
    
    output_file = os.path.join(settings.data_dir, "jobs", job_id, "output.mp4")
    
    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        output_file,
        media_type="video/mp4",
        filename=f"clip_{job_id}.mp4"
    )


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
    elif result.state == "FAILED" or result.state == "FAILURE":
        job["status"] = "failed"
        job["error"] = str(result.info) if result.info else "Unknown error"
    
    # Calculate ETA based on elapsed time and progress
    if job["progress"] > 0 and job["progress"] < 100:
        try:
            created = datetime.fromisoformat(job["created_at"])
            elapsed = (datetime.utcnow() - created).total_seconds()
            # Estimate total time based on progress
            estimated_total = elapsed / (job["progress"] / 100)
            job["eta_seconds"] = max(0, int(estimated_total - elapsed))
        except:
            job["eta_seconds"] = None
    else:
        job["eta_seconds"] = None
