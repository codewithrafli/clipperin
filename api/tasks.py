import os
import subprocess
import uuid
from celery import Celery
from config import settings

# Initialize Celery
celery_app = Celery(
    "tasks",
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(bind=True)
def process_video(self, job_id: str, url: str, options: dict = None):
    """
    Main video processing task:
    1. Download video from YouTube
    2. Generate subtitles with Whisper
    3. Create short clip with FFmpeg
    """
    options = options or {}
    
    # Paths
    data_dir = settings.data_dir
    job_dir = os.path.join(data_dir, "jobs", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    input_file = os.path.join(job_dir, "input.mp4")
    srt_file = os.path.join(job_dir, "input.srt")
    output_file = os.path.join(job_dir, "output.mp4")
    
    try:
        # Step 1: Download video
        self.update_state(state="DOWNLOADING", meta={"progress": 10})
        
        download_cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]",
            "--merge-output-format", "mp4",
            "-o", input_file,
            url
        ]
        subprocess.run(download_cmd, check=True, capture_output=True)
        
        # Step 2: Generate subtitles with Whisper
        self.update_state(state="TRANSCRIBING", meta={"progress": 40})
        
        import whisper
        model = whisper.load_model(settings.whisper_model)
        result = model.transcribe(input_file)
        
        # Write SRT file
        with open(srt_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(result["segments"], 1):
                start = format_timestamp(segment["start"])
                end = format_timestamp(segment["end"])
                text = segment["text"].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
        
        # Step 3: Create clip with FFmpeg
        self.update_state(state="PROCESSING", meta={"progress": 70})
        
        clip_start = options.get("clip_start", settings.clip_start)
        clip_duration = options.get("clip_duration", settings.clip_duration)
        
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(clip_start),
            "-t", str(clip_duration),
            "-i", input_file,
            "-vf", (
                f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
                f"scale={settings.output_width}:{settings.output_height},"
                f"subtitles={srt_file}:force_style='FontName=Arial Black,FontSize=48,Outline=3,Alignment=2',"
                f"eq=contrast=1.05:saturation=1.1"
            ),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", str(settings.output_crf),
            "-c:a", "aac",
            output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        
        self.update_state(state="COMPLETED", meta={"progress": 100})
        
        return {
            "status": "completed",
            "output_file": output_file
        }
        
    except Exception as e:
        self.update_state(state="FAILED", meta={"error": str(e)})
        raise


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
