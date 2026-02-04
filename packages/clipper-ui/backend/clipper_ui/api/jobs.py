"""Jobs API routes."""

import json
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from clipper_ui.schemas.job import (
    JobCreate,
    JobResponse,
    JobStatus,
    ChapterResponse,
    ClipResponse,
    ChapterSelectRequest,
)
from clipper_core import (
    Job,
    VideoDownloader,
    AudioTranscriber,
    ContentAnalyzer,
    VideoRenderer,
    CaptionRenderer,
)
from clipper_core.ai import GeminiClient, GroqClient, OpenAIClient

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# In-memory storage (use Redis/DB in production)
_jobs: dict[str, Job] = {}
_settings: dict = {}


def get_settings() -> dict:
    """Get current settings."""
    return _settings


async def process_job(job_id: str):
    """Background task to process a job."""
    job = _jobs.get(job_id)
    if not job:
        return

    settings = get_settings()
    output_dir = Path("/data/jobs") / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download
        job.update_status(JobStatus.DOWNLOADING, progress=10)
        downloader = VideoDownloader(output_dir=output_dir)
        video_path = downloader.download(job.url, output_path=output_dir / "video.mp4")
        job.video_path = video_path

        # Transcribe
        job.update_status(JobStatus.TRANSCRIBING, progress=30)
        transcriber = AudioTranscriber()
        result = transcriber.transcribe(video_path)
        srt_path = output_dir / "subtitles.srt"
        transcriber.to_srt(result, srt_path)
        job.srt_path = srt_path
        job.transcription = result.segments

        # Analyze
        job.update_status(JobStatus.ANALYZING, progress=60)
        ai_client = None
        ai_provider = settings.get("ai_provider", "none")

        if ai_provider != "none":
            match ai_provider:
                case "gemini":
                    ai_client = GeminiClient(api_key=settings.get("gemini_api_key"))
                case "groq":
                    ai_client = GroqClient(api_key=settings.get("groq_api_key"))
                case "openai":
                    ai_client = OpenAIClient(api_key=settings.get("openai_api_key"))

        analyzer = ContentAnalyzer(ai_client=ai_client)
        transcription_text = " ".join([s.get("text", "") for s in result.segments])
        chapters = analyzer.analyze_chapters(
            transcription_text,
            result.duration,
            use_ai=job.use_ai,
        )
        job.chapters = chapters

        # Save chapters
        chapters_path = output_dir / "chapters.json"
        with open(chapters_path, "w") as f:
            json.dump({
                "chapters": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "start": c.start,
                        "end": c.end,
                        "duration": c.duration,
                        "summary": c.summary,
                        "confidence": c.confidence,
                        "hooks": c.hooks,
                    }
                    for c in chapters
                ]
            }, f, indent=2)

        job.update_status(JobStatus.CHAPTERS_READY, progress=100)

    except Exception as e:
        job.update_status(JobStatus.FAILED, error=str(e))


async def render_job(job_id: str, chapter_ids: List[str], options: dict):
    """Background task to render clips."""
    job = _jobs.get(job_id)
    if not job:
        return

    output_dir = Path("/data/jobs") / job_id

    try:
        job.update_status(JobStatus.PROCESSING, progress=0)

        # Filter chapters
        chapters_to_render = [c for c in job.chapters if c.id in chapter_ids]

        # Setup renderer
        from clipper_core.models.config import OutputConfig, AspectRatio, CaptionStyle

        aspect = AspectRatio.PORTRAIT
        if options.get("output_aspect_ratio") == "1:1":
            aspect = AspectRatio.SQUARE
        elif options.get("output_aspect_ratio") == "4:5":
            aspect = AspectRatio.VERTICAL

        config = OutputConfig(
            aspect_ratio=aspect,
            enable_progress_bar=options.get("enable_progress_bar", True),
            progress_bar_color=options.get("progress_bar_color", "#FF0050"),
        )

        renderer = VideoRenderer(output_config=config)
        caption_renderer = CaptionRenderer()

        # Get caption style
        caption_style = None
        for style in CaptionStyle.get_default_styles():
            if style.id == options.get("caption_style", "default"):
                caption_style = style
                break

        # Render clips
        for i, chapter in enumerate(chapters_to_render):
            progress = (i / len(chapters_to_render)) * 100
            job.update_status(JobStatus.PROCESSING, progress=progress)

            clip_filename = f"clip_{chapter.id[:8]}.mp4"
            clip_path = output_dir / clip_filename

            hook_text = ""
            if options.get("enable_auto_hook") and chapter.hooks:
                hook_text = chapter.hooks[0]

            result = renderer.render_clip(
                input_path=job.video_path,
                output_path=clip_path,
                start=chapter.start,
                end=chapter.end,
                caption_style=caption_style,
                srt_path=job.srt_path,
                enable_hook=options.get("enable_auto_hook", False),
                hook_text=hook_text,
                enable_smart_reframe=options.get("enable_smart_reframe", False),
                enable_progress_bar=options.get("enable_progress_bar", True),
                progress_bar_color=options.get("progress_bar_color", "#FF0050"),
                aspect_ratio=aspect,
            )

            if result.success:
                thumb_path = output_dir / f"thumb_{chapter.id[:8]}.jpg"
                renderer.generate_thumbnail(clip_path, thumb_path)

                clip = ClipResponse(
                    filename=clip_filename,
                    title=chapter.title,
                    start=chapter.start,
                    end=chapter.end,
                    duration=chapter.duration,
                    thumbnail=thumb_path.name if thumb_path.exists() else None,
                )
                job.clips.append(clip)

        job.update_status(JobStatus.COMPLETED, progress=100)

    except Exception as e:
        job.update_status(JobStatus.FAILED, error=str(e))


@router.get("", response_model=List[JobResponse])
async def list_jobs():
    """List all jobs."""
    return [
        JobResponse(
            id=j.id,
            url=j.url,
            status=JobStatus(j.status.value),
            progress=j.progress,
            created_at=j.created_at,
            updated_at=j.updated_at,
            error=j.error,
            chapters=[ChapterResponse.model_validate(c) for c in j.chapters],
            clips=[ClipResponse.model_validate(c) for c in j.clips],
            metadata=j.metadata,
        )
        for j in _jobs.values()
    ]


@router.post("", response_model=JobResponse)
async def create_job(request: JobCreate, background_tasks: BackgroundTasks):
    """Create a new clipping job."""
    job = Job(
        id=str(uuid4()),
        url=request.url,
        caption_style=request.caption_style,
        use_ai=request.use_ai_detection,
        enable_auto_hook=request.enable_auto_hook,
        enable_smart_reframe=request.enable_smart_reframe,
        enable_dynamic_layout=request.enable_dynamic_layout,
    )

    _jobs[job.id] = job

    background_tasks.add_task(process_job, job.id)

    return JobResponse(
        id=job.id,
        url=job.url,
        status=JobStatus(job.status.value),
        progress=job.progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job status."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        url=job.url,
        status=JobStatus(job.status.value),
        progress=job.progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
        chapters=[ChapterResponse.model_validate(c) for c in job.chapters],
        clips=[ClipResponse.model_validate(c) for c in job.clips],
        metadata=job.metadata,
    )


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete files
    job_dir = Path("/data/jobs") / job_id
    if job_dir.exists():
        import shutil
        shutil.rmtree(job_dir)

    del _jobs[job_id]
    return {"deleted": True}


@router.get("/{job_id}/chapters", response_model=List[ChapterResponse])
async def get_job_chapters(job_id: str):
    """Get job chapters."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return [ChapterResponse.model_validate(c) for c in job.chapters]


@router.post("/{job_id}/select-chapters")
async def select_chapters(job_id: str, request: ChapterSelectRequest, background_tasks: BackgroundTasks):
    """Select chapters and start rendering."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.CHAPTERS_READY:
        raise HTTPException(status_code=400, detail="Job is not ready for rendering")

    job.clips.clear()  # Clear any existing clips
    background_tasks.add_task(render_job, job_id, request.chapter_ids, request.options)

    return {"rendering": True, "clip_count": len(request.chapter_ids)}


@router.get("/{job_id}/download")
async def download_clip(job_id: str, filename: str):
    """Download a rendered clip."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    clip_path = Path("/data/jobs") / job_id / filename
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(clip_path, filename=filename)


@router.get("/{job_id}/thumbnail/{thumbnail}")
async def get_thumbnail(job_id: str, thumbnail: str):
    """Get clip thumbnail."""
    thumb_path = Path("/data/jobs") / job_id / thumbnail
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(thumb_path)
