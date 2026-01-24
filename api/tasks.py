import os
import subprocess
from datetime import datetime
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


def log_progress(job_dir: str, message: str):
    """Write progress message to job log file"""
    log_file = os.path.join(job_dir, "progress.log")
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


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
        log_progress(job_dir, "🚀 Starting job...")
        log_progress(job_dir, f"📎 URL: {url}")
        self.update_state(state="DOWNLOADING", meta={"progress": 10})
        log_progress(job_dir, "⬇️ Downloading video from YouTube...")
        
        download_cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]",
            "--merge-output-format", "mp4",
            "-o", input_file,
            url
        ]
        subprocess.run(download_cmd, check=True, capture_output=True)
        log_progress(job_dir, "✅ Download complete!")
        
        # Get video duration
        try:
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                        "-of", "default=noprint_wrappers=1:nokey=1", input_file]
            duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(duration_result.stdout.strip())
            log_progress(job_dir, f"📹 Video duration: {int(duration//60)}m {int(duration%60)}s")
        except:
            duration = 0
        
        # Step 2: Generate subtitles with Whisper
        self.update_state(state="TRANSCRIBING", meta={"progress": 40})
        log_progress(job_dir, f"🎧 Loading Whisper model ({settings.whisper_model})...")
        
        import whisper
        model = whisper.load_model(settings.whisper_model)
        log_progress(job_dir, "🎧 Transcribing audio... (this may take a while)")
        
        result = model.transcribe(input_file, verbose=False)
        
        # Write SRT file with progress logging
        segments = result["segments"]
        log_progress(job_dir, f"📝 Found {len(segments)} subtitle segments")
        
        with open(srt_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start = format_timestamp(segment["start"])
                end = format_timestamp(segment["end"])
                text = segment["text"].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
        
        # Show transcript preview in logs
        log_progress(job_dir, "📜 Transcript preview:")
        preview_count = min(5, len(segments))
        for i, seg in enumerate(segments[:preview_count]):
            time_str = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
            text_preview = seg["text"].strip()[:60]
            if len(seg["text"].strip()) > 60:
                text_preview += "..."
            log_progress(job_dir, f"   [{time_str}] {text_preview}")
        
        if len(segments) > preview_count:
            log_progress(job_dir, f"   ... and {len(segments) - preview_count} more segments")
        
        log_progress(job_dir, "✅ Transcription complete!")
        
        # Step 3: Create clip with FFmpeg
        self.update_state(state="PROCESSING", meta={"progress": 70})
        
        clip_start = options.get("clip_start", settings.clip_start)
        clip_duration = options.get("clip_duration", settings.clip_duration)
        
        log_progress(job_dir, f"✂️ Creating clip: {clip_start}s to {clip_start + clip_duration}s")
        log_progress(job_dir, "🎬 Processing video with FFmpeg...")
        
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
        
        log_progress(job_dir, "✅ Video processing complete!")
        log_progress(job_dir, "🎉 Job finished successfully!")
        
        self.update_state(state="COMPLETED", meta={"progress": 100})
        
        return {
            "status": "completed",
            "output_file": output_file
        }
        
    except Exception as e:
        log_progress(job_dir, f"❌ Error: {str(e)}")
        self.update_state(state="FAILED", meta={"error": str(e)})
        raise


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
