import os
import subprocess
import re
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


# Caption Style Templates
CAPTION_STYLES = {
    "default": {
        "name": "Default",
        "style": "FontName=Arial Black,FontSize=14,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Shadow=1,Alignment=2,MarginV=50"
    },
    "karaoke": {
        "name": "Karaoke",
        "style": "FontName=Impact,FontSize=16,PrimaryColour=&H00FF00,SecondaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=3,Shadow=0,Alignment=2,MarginV=50,Bold=1"
    },
    "minimal": {
        "name": "Minimal",
        "style": "FontName=Helvetica,FontSize=12,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=1,Shadow=0,Alignment=2,MarginV=40"
    },
    "bold": {
        "name": "Bold Pop",
        "style": "FontName=Impact,FontSize=18,PrimaryColour=&H00FFFF,OutlineColour=&H000000,Outline=4,Shadow=2,Alignment=2,MarginV=60,Bold=1"
    },
    "neon": {
        "name": "Neon Glow",
        "style": "FontName=Arial Black,FontSize=15,PrimaryColour=&HFF00FF,OutlineColour=&H000000,Outline=3,Shadow=0,Alignment=2,MarginV=50,Bold=1"
    },
    "podcast": {
        "name": "Podcast",
        "style": "FontName=Georgia,FontSize=13,PrimaryColour=&HFFFFFF,OutlineColour=&H333333,Outline=2,Shadow=1,Alignment=2,MarginV=45"
    }
}


def analyze_transcript_for_clips(segments: list, target_duration: int = 30) -> list:
    """
    Smart Clip Detection using rule-based analysis.
    Returns top 5 potential viral clip timestamps.
    """
    if not segments:
        return []
    
    # Keywords that indicate engaging content
    viral_keywords = {
        # Questions (hook attention)
        "apa": 2, "kenapa": 2, "bagaimana": 2, "gimana": 2, "mengapa": 2,
        "siapa": 2, "kapan": 2, "dimana": 2, "berapa": 2,
        # Strong emotions
        "gila": 3, "wow": 3, "luar biasa": 3, "amazing": 3, "incredible": 3,
        "keren": 2, "hebat": 2, "mantap": 2, "dahsyat": 2,
        # Secrets/insights
        "rahasia": 4, "secret": 4, "tips": 3, "trik": 3, "hack": 3,
        "cara": 2, "strategi": 2, "jangan": 2,
        # Controversy/contrast
        "tapi": 2, "padahal": 2, "sebenarnya": 3, "ternyata": 3,
        "salah": 2, "benar": 2, "bohong": 3,
        # Numbers/lists
        "pertama": 2, "kedua": 2, "ketiga": 2, "terakhir": 2,
        "nomor satu": 3, "paling": 2,
        # Call to action
        "harus": 2, "wajib": 2, "penting": 3, "kunci": 2,
    }
    
    # Score each segment
    scored_segments = []
    for i, seg in enumerate(segments):
        text = seg["text"].lower()
        score = 0
        reasons = []
        
        # Keyword scoring
        for keyword, weight in viral_keywords.items():
            if keyword in text:
                score += weight
                reasons.append(f"keyword:{keyword}")
        
        # Question mark bonus
        if "?" in seg["text"]:
            score += 2
            reasons.append("question")
        
        # Exclamation bonus
        if "!" in seg["text"]:
            score += 1
            reasons.append("exclamation")
        
        # Short, punchy statements (hook potential)
        word_count = len(text.split())
        if 3 <= word_count <= 10:
            score += 1
            reasons.append("short_punchy")
        
        # Beginning of video bonus (good hooks)
        if i < 5:
            score += 1
            reasons.append("intro")
        
        scored_segments.append({
            "index": i,
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
            "score": score,
            "reasons": reasons
        })
    
    # Sort by score and get top clips
    scored_segments.sort(key=lambda x: x["score"], reverse=True)
    
    # Group nearby segments for clip windows
    clips = []
    used_times = set()
    
    for seg in scored_segments:
        if len(clips) >= 5:
            break
        
        start_time = max(0, seg["start"] - 2)  # Start 2 seconds before hook
        
        # Check if this time range overlaps with existing clips
        time_key = int(start_time / 30)  # 30-second windows
        if time_key in used_times:
            continue
        
        used_times.add(time_key)
        
        clips.append({
            "start": start_time,
            "duration": target_duration,
            "score": seg["score"],
            "hook": seg["text"][:50],
            "reasons": seg["reasons"][:3]
        })
    
    return clips


def analyze_transcript_with_ai(segments: list, target_duration: int = 30) -> list:
    """
    Smart Clip Detection using Gemini or OpenAI API.
    Returns top 5 potential viral clip timestamps.
    """
    if not segments:
        return []
    
    # Build transcript text with timestamps
    transcript_text = ""
    for seg in segments:
        time_str = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
        transcript_text += f"[{time_str}] {seg['text'].strip()}\n"
    
    prompt = f"""Analyze this video transcript and identify the TOP 5 most viral/engaging moments that would make great short clips (TikTok/Reels/Shorts style).

For each moment, provide:
1. timestamp (in MM:SS format)
2. virality_score (1-10)
3. reason (hook, controversy, insight, humor, emotion, etc.)
4. hook_text (the actual text that makes it engaging)

Transcript:
{transcript_text[:4000]}

Return as JSON array:
[{{"timestamp": "01:23", "score": 8, "reason": "strong hook", "hook": "text here"}}]

Only return the JSON array, nothing else."""

    clips = []
    
    # Try Gemini first
    if settings.gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            clips = parse_ai_response(response.text, segments, target_duration)
            if clips:
                return clips
        except Exception as e:
            print(f"Gemini API error: {e}")
    
    # Try OpenAI
    if settings.openai_api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            clips = parse_ai_response(response.choices[0].message.content, segments, target_duration)
            if clips:
                return clips
        except Exception as e:
            print(f"OpenAI API error: {e}")
    
    return clips


def parse_ai_response(response_text: str, segments: list, target_duration: int) -> list:
    """Parse AI response and convert to clip format"""
    import json
    
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not json_match:
            return []
        
        ai_clips = json.loads(json_match.group())
        clips = []
        
        for item in ai_clips[:5]:
            timestamp = item.get("timestamp", "00:00")
            parts = timestamp.split(":")
            if len(parts) == 2:
                start_seconds = int(parts[0]) * 60 + int(parts[1])
            else:
                start_seconds = 0
            
            clips.append({
                "start": max(0, start_seconds - 2),
                "duration": target_duration,
                "score": item.get("score", 5),
                "hook": item.get("hook", "")[:50],
                "reasons": [item.get("reason", "ai_detected")]
            })
        
        return clips
    except Exception as e:
        print(f"Failed to parse AI response: {e}")
        return []


def smart_detect_clips(segments: list, target_duration: int = 30, use_ai: bool = True) -> tuple:
    """
    Hybrid Smart Clip Detection.
    Returns (clips, method_used)
    """
    # Check if AI is available and requested
    ai_available = bool(settings.gemini_api_key or settings.openai_api_key)
    
    if use_ai and ai_available:
        clips = analyze_transcript_with_ai(segments, target_duration)
        if clips:
            return clips, "ai"
    
    # Fallback to rule-based
    clips = analyze_transcript_for_clips(segments, target_duration)
    return clips, "rule-based"


def create_clip_srt(original_srt: str, clip_srt: str, start_time: float, duration: float):
    """Create a new SRT file adjusted for clip timing"""
    with open(original_srt, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Parse SRT format
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    end_time = start_time + duration
    new_srt = []
    counter = 1
    
    for idx, start_ts, end_ts, text in matches:
        # Parse timestamps
        start_secs = timestamp_to_seconds(start_ts)
        end_secs = timestamp_to_seconds(end_ts)
        
        # Check if segment is within clip range
        if end_secs < start_time or start_secs > end_time:
            continue
        
        # Adjust timing relative to clip start
        new_start = max(0, start_secs - start_time)
        new_end = min(duration, end_secs - start_time)
        
        if new_end > new_start:
            new_srt.append(f"{counter}")
            new_srt.append(f"{seconds_to_timestamp(new_start)} --> {seconds_to_timestamp(new_end)}")
            new_srt.append(text.strip())
            new_srt.append("")
            counter += 1
    
    with open(clip_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(new_srt))


def timestamp_to_seconds(ts: str) -> float:
    """Convert SRT timestamp to seconds"""
    parts = ts.replace(",", ".").split(":")
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])


def seconds_to_timestamp(secs: float) -> str:
    """Convert seconds to SRT timestamp"""
    hours = int(secs // 3600)
    minutes = int((secs % 3600) // 60)
    seconds = int(secs % 60)
    millis = int((secs % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


@celery_app.task(bind=True)
def process_video(self, job_id: str, url: str, options: dict = None):
    """
    Main video processing task:
    1. Download video from YouTube
    2. Generate subtitles with Whisper
    3. Smart Clip Detection
    4. Create short clip with FFmpeg
    """
    options = options or {}
    
    # Paths
    data_dir = settings.data_dir
    job_dir = os.path.join(data_dir, "jobs", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    input_file = os.path.join(job_dir, "input.mp4")
    srt_file = os.path.join(job_dir, "input.srt")
    clip_srt_file = os.path.join(job_dir, "clip.srt")
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
            video_duration = float(duration_result.stdout.strip())
            log_progress(job_dir, f"📹 Video duration: {int(video_duration//60)}m {int(video_duration%60)}s")
        except:
            video_duration = 0
        
        # Step 2: Generate subtitles with Whisper
        self.update_state(state="TRANSCRIBING", meta={"progress": 40})
        log_progress(job_dir, f"🎧 Loading Whisper model ({settings.whisper_model})...")
        
        import whisper
        model = whisper.load_model(settings.whisper_model)
        log_progress(job_dir, "🎧 Transcribing audio... (this may take a while)")
        
        result = model.transcribe(input_file, verbose=False)
        
        # Write SRT file
        segments = result["segments"]
        log_progress(job_dir, f"📝 Found {len(segments)} subtitle segments")
        
        with open(srt_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start = format_timestamp(segment["start"])
                end = format_timestamp(segment["end"])
                text = segment["text"].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
        
        # Show transcript preview
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
        
        # Step 3: Smart Clip Detection
        log_progress(job_dir, "🧠 Analyzing transcript for viral moments...")
        
        clip_duration = options.get("clip_duration", settings.clip_duration)
        use_ai = options.get("use_ai_detection", True)
        
        suggested_clips, detection_method = smart_detect_clips(segments, clip_duration, use_ai)
        
        if detection_method == "ai":
            log_progress(job_dir, "🤖 Using AI-powered detection (Gemini/OpenAI)")
        else:
            log_progress(job_dir, "📊 Using rule-based detection (free)")
        
        if suggested_clips:
            log_progress(job_dir, f"🎯 Found {len(suggested_clips)} potential viral clips:")
            for i, clip in enumerate(suggested_clips[:3], 1):
                time_str = f"{int(clip['start']//60):02d}:{int(clip['start']%60):02d}"
                log_progress(job_dir, f"   #{i} [{time_str}] Score: {clip['score']} - \"{clip['hook']}...\"")
        
        # Use provided start time or best detected clip
        if options.get("clip_start") is not None:
            clip_start = options["clip_start"]
            log_progress(job_dir, f"📍 Using custom start time: {clip_start}s")
        elif options.get("auto_detect", True) and suggested_clips:
            clip_start = suggested_clips[0]["start"]
            log_progress(job_dir, f"🎯 Auto-selected best clip at {int(clip_start)}s")
        else:
            clip_start = settings.clip_start
            log_progress(job_dir, f"📍 Using default start time: {clip_start}s")
        
        # Step 4: Create clip with FFmpeg
        self.update_state(state="PROCESSING", meta={"progress": 70})
        
        log_progress(job_dir, f"✂️ Creating clip: {int(clip_start)}s to {int(clip_start + clip_duration)}s")
        
        # Create adjusted SRT for the clip
        create_clip_srt(srt_file, clip_srt_file, clip_start, clip_duration)
        log_progress(job_dir, "📝 Adjusted subtitles for clip timing")
        
        # Get caption style
        style_name = options.get("caption_style", "default")
        style = CAPTION_STYLES.get(style_name, CAPTION_STYLES["default"])
        log_progress(job_dir, f"🎨 Using caption style: {style['name']}")
        
        log_progress(job_dir, "🎬 Processing video with FFmpeg...")
        
        # FFmpeg with proper timing - use -ss AFTER -i to avoid subtitle sync issues
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-ss", str(clip_start),
            "-t", str(clip_duration),
            "-vf", (
                f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
                f"scale={settings.output_width}:{settings.output_height},"
                f"subtitles={clip_srt_file}:force_style='{style['style']}',"
                f"eq=contrast=1.05:saturation=1.1"
            ),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", str(settings.output_crf),
            "-c:a", "aac",
            "-b:a", "128k",
            output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        
        log_progress(job_dir, "✅ Video processing complete!")
        log_progress(job_dir, "🎉 Job finished successfully!")
        
        # Save suggested clips for later use
        clips_file = os.path.join(job_dir, "suggested_clips.json")
        import json
        with open(clips_file, "w") as f:
            json.dump(suggested_clips, f, indent=2)
        
        self.update_state(state="COMPLETED", meta={"progress": 100})
        
        return {
            "status": "completed",
            "output_file": output_file,
            "suggested_clips": suggested_clips[:5]
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
