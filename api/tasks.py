import os
import subprocess
import re
from datetime import datetime
from celery import Celery

# Handle both package import (from .config) and standalone import (from config)
try:
    from .config import settings
except ImportError:
    from config import settings

import cv2
import tempfile
import numpy as np

# =============================================================================
# AI PROVIDER INTEGRATION (Groq, Gemini, OpenAI)
# =============================================================================

def get_ai_client():
    """Get the configured AI client based on settings"""
    # Reload settings in worker process
    settings.load_dynamic_settings()
    
    provider = settings.ai_provider.lower()

    if provider == "groq" and settings.groq_api_key:
        try:
            from groq import Groq
            return ("groq", Groq(api_key=settings.groq_api_key))
        except ImportError:
            print("Groq package not installed, falling back to Gemini")

    if provider == "gemini" and settings.gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            return ("gemini", client)
        except ImportError:
            try:
                import google.generativeai as genai_old
                genai_old.configure(api_key=settings.gemini_api_key)
                return ("gemini_old", genai_old)
            except ImportError:
                pass

    if provider == "openai" and settings.openai_api_key:
        try:
            from openai import OpenAI
            return ("openai", OpenAI(api_key=settings.openai_api_key))
        except ImportError:
            pass

    return ("none", None)


def generate_hook_text_ai(transcript_text: str, max_words: int = 8) -> str:
    """Generate viral hook text using AI"""
    provider, client = get_ai_client()

    prompt = f"""Generate a viral video hook (maximum {max_words} words) for this transcript.
Rules:
- Make it curiosity-driven, emotional, or shocking
- Use UPPERCASE for emphasis
- Must grab attention in first 2 seconds
- No quotes, just the hook text

Transcript (first 500 chars):
{transcript_text[:500]}

Hook:"""

    try:
        if provider == "groq":
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()

        elif provider == "gemini":
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text.strip()

        elif provider == "gemini_old":
            model = client.GenerativeModel("gemini-pro")
            response = model.generate_content(prompt)
            return response.text.strip()

        elif provider == "openai":
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"AI hook generation failed: {e}")

    # Fallback to rule-based
    return generate_hook_text_rules(transcript_text, max_words)


def generate_hook_text_rules(transcript_text: str, max_words: int = 8) -> str:
    """Generate hook text using rule-based analysis (FREE)"""
    hook_keywords = [
        "rahasia", "ternyata", "gila", "shocking", "penting",
        "harus", "jangan", "stop", "cara", "tips", "secret",
        "why", "how", "truth", "real", "actually", "never",
        "always", "best", "worst", "pertama", "nomor satu"
    ]

    sentences = transcript_text.replace("?", "? ").replace("!", "! ").replace(".", ". ").split()

    # Find sentence with most hook keywords
    best_hook = None
    best_score = 0

    # Split into chunks of ~10 words
    chunks = []
    for i in range(0, len(sentences), 10):
        chunk = " ".join(sentences[i:i+10])
        chunks.append(chunk)

    for chunk in chunks[:10]:  # Check first 10 chunks
        score = sum(1 for kw in hook_keywords if kw.lower() in chunk.lower())
        if "?" in chunk:
            score += 2
        if "!" in chunk:
            score += 1

        if score > best_score:
            best_score = score
            best_hook = chunk

    if best_hook:
        # Truncate to max words and uppercase
        words = best_hook.split()[:max_words]
        return " ".join(words).upper()

    # Ultimate fallback
    return "TONTON SAMPAI HABIS!"


def add_hook_overlay(input_video: str, output_video: str, hook_text: str,
                     duration: int = 5, style: str = "bold") -> bool:
    """Add animated hook text overlay to video using FFmpeg"""

    # Escape special characters for FFmpeg
    # 1. Escape backslashes first (so we don't double escape later additions)
    escaped_text = hook_text.replace("\\", "\\\\")
    # 2. Escape colons (filter separator)
    escaped_text = escaped_text.replace(":", "\\:")
    # 3. Escape single quotes (we are inside text='...')
    escaped_text = escaped_text.replace("'", "'\\''")

    # Style configurations
    styles = {
        "bold": {
            "fontsize": 60,
            "fontcolor": "white",
            "borderw": 4,
            "bordercolor": "black",
            "y_pos": "h*0.12"
        },
        "minimal": {
            "fontsize": 48,
            "fontcolor": "white",
            "borderw": 2,
            "bordercolor": "black@0.5",
            "y_pos": "h*0.10"
        },
        "neon": {
            "fontsize": 55,
            "fontcolor": "#FF00FF",
            "borderw": 3,
            "bordercolor": "#00FFFF",
            "y_pos": "h*0.15"
        }
    }

    s = styles.get(style, styles["bold"])

    # FFmpeg drawtext filter with fade animation
    drawtext_filter = (
        f"drawtext=text='{escaped_text}'"
        f":fontsize={s['fontsize']}"
        f":fontcolor={s['fontcolor']}"
        f":borderw={s['borderw']}"
        f":bordercolor={s['bordercolor']}"
        f":x=(w-text_w)/2"
        f":y={s['y_pos']}"
        f":enable='lt(t,{duration})'"
        f":alpha='if(lt(t,0.5),t*2,if(gt(t,{duration-0.5}),({duration}-t)*2,1))'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", drawtext_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", str(settings.output_crf),
        "-c:a", "copy",
        output_video
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        return True
    except Exception as e:
        print(f"Hook overlay failed: {e}")
        return False


# =============================================================================
# SMART REFRAME (Face Tracking with OpenCV - FREE)
# =============================================================================

def smart_reframe_video(input_path: str, output_path: str,
                        target_w: int = 1080, target_h: int = 1920,
                        smoothing: float = 0.15) -> bool:
    """
    Smart reframe video to track speaker face (100% FREE with OpenCV)
    Keeps the speaker centered in vertical frame
    """

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Cannot open video: {input_path}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate crop dimensions to match target aspect ratio
    target_ar = target_w / target_h
    orig_ar = orig_w / orig_h

    if orig_ar > target_ar:
        # Video is wider - crop width
        crop_h = orig_h
        crop_w = int(orig_h * target_ar)
    else:
        # Video is taller - crop height
        crop_w = orig_w
        crop_h = int(orig_w / target_ar)

    # Temp output without audio
    temp_output = output_path.replace('.mp4', '_temp.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_output, fourcc, fps, (target_w, target_h))

    last_center_x = orig_w // 2
    last_center_y = orig_h // 2
    detect_every_n = 3  # Detect face every N frames for performance

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect face periodically
        if frame_count % detect_every_n == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80)
            )

            if len(faces) > 0:
                # Get largest face (primary speaker)
                largest = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest
                face_center_x = x + w // 2
                face_center_y = y + h // 2

                # Smooth transition
                last_center_x = int(last_center_x * (1 - smoothing) + face_center_x * smoothing)
                last_center_y = int(last_center_y * (1 - smoothing) + face_center_y * smoothing)

        # Calculate crop position (keep face centered)
        crop_x = last_center_x - crop_w // 2
        crop_y = last_center_y - crop_h // 2

        # Clamp to valid range
        crop_x = max(0, min(crop_x, orig_w - crop_w))
        crop_y = max(0, min(crop_y, orig_h - crop_h))

        # Crop and resize
        cropped = frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
        resized = cv2.resize(cropped, (target_w, target_h))

        out.write(resized)
        frame_count += 1

        # Progress logging every 10%
        if frame_count % (total_frames // 10 + 1) == 0:
            progress = int(frame_count / total_frames * 100)
            print(f"Reframe progress: {progress}%", flush=True)

    cap.release()
    out.release()

    # Merge audio from original video
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_output,
            "-i", input_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0?",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)

        # Clean up temp file
        if os.path.exists(temp_output):
            os.remove(temp_output)

        return True
    except Exception as e:
        print(f"Audio merge failed: {e}")
        # Fallback: use video without audio
        if os.path.exists(temp_output):
            os.rename(temp_output, output_path)
        return True


# =============================================================================
# COST ESTIMATION (IDR)
# =============================================================================

def estimate_cost_idr(options: dict) -> dict:
    """Calculate estimated cost in IDR based on selected features"""
    provider = settings.ai_provider.lower()
    total = 0
    breakdown = []

    # Transcription (always free - local Whisper)
    breakdown.append({"feature": "Transcription (Whisper)", "cost": 0, "note": "FREE - Local"})

    # Hook generation
    if options.get("enable_auto_hook"):
        if provider == "gemini":
            cost = settings.cost_hook_gemini
            note = "FREE tier"
        elif provider == "groq":
            cost = settings.cost_hook_groq
            note = "~Rp15/video"
        elif provider == "openai":
            cost = settings.cost_hook_openai
            note = "~Rp250/video"
        else:
            cost = 0
            note = "Rule-based (FREE)"

        breakdown.append({"feature": "Auto Hook", "cost": cost, "note": note})
        total += cost

    # Smart Reframe (always free - OpenCV)
    if options.get("enable_smart_reframe"):
        breakdown.append({"feature": "Smart Reframe", "cost": 0, "note": "FREE - OpenCV"})

    # Chapter Analysis
    if provider in ["gemini", "groq", "openai"]:
        if provider == "gemini":
            cost = 0
            note = "FREE tier"
        elif provider == "groq":
            cost = 25
            note = "~Rp25/video"
        elif provider == "openai":
            cost = 400
            note = "~Rp400/video"
        breakdown.append({"feature": "AI Chapter Analysis", "cost": cost, "note": note})
        total += cost

    return {
        "total_idr": total,
        "total_display": f"Rp {total:,}".replace(",", "."),
        "breakdown": breakdown,
        "provider": provider
    }


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
    },
    "capcut": {
        "name": "CapCut (Dynamic)",
        "style": "FontName=Impact,FontSize=24,PrimaryColour=&H00FFFFFF,SecondaryColour=&H00000000,OutlineColour=&H00000000,BackColour=&H80000000,Outline=4,Shadow=2,Bold=1,Alignment=2,MarginV=100,BorderStyle=4",
        "dynamic": True,
        "use_background": True
    },
    "capcut_yellow": {
        "name": "CapCut Yellow Box",
        "style": "FontName=Impact,FontSize=26,PrimaryColour=&H00000000,SecondaryColour=&H00000000,OutlineColour=&H00000000,BackColour=&H0000FFFF,Outline=0,Shadow=0,Bold=1,Alignment=2,MarginV=100,BorderStyle=4",
        "dynamic": True,
        "use_background": True
    },
    "capcut_red": {
        "name": "CapCut Red Box",
        "style": "FontName=Impact,FontSize=26,PrimaryColour=&H00FFFFFF,SecondaryColour=&H00000000,OutlineColour=&H00000000,BackColour=&H000000FF,Outline=0,Shadow=0,Bold=1,Alignment=2,MarginV=100,BorderStyle=4",
        "dynamic": True,
        "use_background": True
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
        if len(clips) >= 9:  # Increased from 5 to 9 (like OpusClip)
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
            # Try new package first
            try:
                from google import genai
                client = genai.Client(api_key=settings.gemini_api_key)
                response = client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents=prompt
                )
                clips = parse_ai_response(response.text, segments, target_duration)
                if clips:
                    return clips
            except ImportError:
                # Fallback to old package (will be deprecated)
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                # Use gemini-pro which is stable and widely available
                model = genai.GenerativeModel('gemini-pro')
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
        try:
            clips = analyze_transcript_with_ai(segments, target_duration)
            if clips:
                return clips, "ai"
            else:
                print("AI detection returned no clips, falling back to rule-based")
        except Exception as e:
            print(f"AI detection failed: {e}, falling back to rule-based")

    # Fallback to rule-based (always works)
    clips = analyze_transcript_for_clips(segments, target_duration)
    return clips, "rule-based"


# =============================================================================
# CHAPTER ANALYSIS FUNCTIONS (New Feature)
# =============================================================================

def analyze_chapters_with_ai(
    segments: list,
    video_duration: float,
    min_chapter_duration: int = None,
    max_chapter_duration: int = None
) -> list:
    """
    AI-powered semantic chapter analysis.
    Returns chapters with titles, summaries, and keywords (2-5 minutes each).
    """
    if not segments:
        return []

    min_dur = min_chapter_duration or settings.min_chapter_duration
    max_dur = max_chapter_duration or settings.max_chapter_duration

    # Build full transcript with timestamps
    transcript_text = ""
    for seg in segments:
        time_str = f"[{int(seg['start']//60):02d}:{int(seg['start']%60):02d}]"
        transcript_text += f"{time_str} {seg['text'].strip()}\n"

    prompt = f"""Analyze this video transcript and divide it into logical chapters based on topic changes.

Video Duration: {int(video_duration//60)} minutes {int(video_duration%60)} seconds

Requirements for each chapter:
- Duration: {min_dur//60}-{max_dur//60} minutes ({min_dur}-{max_dur} seconds)
- Title: 10-30 characters, descriptive of the main topic
- Summary: 50-100 characters, captures the main point
- Keywords: 3-5 relevant terms/concepts

Important:
- Divide by SEMANTIC content, not just time
- Each chapter should cover a complete topic/idea
- Ensure ALL video content is covered (no gaps)
- Chapters should be meaningful and standalone

Transcript:
{transcript_text[:12000]}

Return as JSON array (ONLY the array, no other text):
[{{"title": "Chapter Title Here", "start_time": "MM:SS", "end_time": "MM:SS", "summary": "Brief summary of this chapter content", "keywords": ["keyword1", "keyword2", "keyword3"]}}]"""

    chapters = []

    # Use configured AI provider via get_ai_client()
    provider, client = get_ai_client()

    try:
        if provider == "groq" and client:
            # Groq (Llama 3.3)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            )
            chapters = parse_chapter_response(response.choices[0].message.content, video_duration)
            if chapters:
                print(f"✅ Groq chapter analysis: Found {len(chapters)} chapters")
                return chapters

        elif provider == "gemini" and client:
            # Gemini
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            chapters = parse_chapter_response(response.text, video_duration)
            if chapters:
                print(f"✅ Gemini chapter analysis: Found {len(chapters)} chapters")
                return chapters

        elif provider == "gemini_old" and client:
            # Legacy Gemini
            model = client.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            chapters = parse_chapter_response(response.text, video_duration)
            if chapters:
                return chapters

        elif provider == "openai" and client:
            # OpenAI
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            chapters = parse_chapter_response(response.choices[0].message.content, video_duration)
            if chapters:
                print(f"✅ OpenAI chapter analysis: Found {len(chapters)} chapters")
                return chapters

    except Exception as e:
        print(f"WARNING: {provider} chapter analysis error: {e}")

    return chapters


def parse_chapter_response(response_text: str, video_duration: float) -> list:
    """Parse AI response into chapter objects"""
    import json

    try:
        # Extract JSON array from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not json_match:
            return []

        ai_chapters = json.loads(json_match.group())
        chapters = []

        for i, item in enumerate(ai_chapters):
            # Parse timestamps (support MM:SS and HH:MM:SS)
            start_str = item.get("start_time", "00:00")
            end_str = item.get("end_time", "00:00")

            start_parts = start_str.split(":")
            end_parts = end_str.split(":")

            if len(start_parts) == 2:
                start_secs = int(start_parts[0]) * 60 + int(start_parts[1])
            elif len(start_parts) == 3:
                start_secs = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + int(start_parts[2])
            else:
                start_secs = 0

            if len(end_parts) == 2:
                end_secs = int(end_parts[0]) * 60 + int(end_parts[1])
            elif len(end_parts) == 3:
                end_secs = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + int(end_parts[2])
            else:
                end_secs = start_secs + 180  # Default 3 minutes

            # Validate duration
            duration = end_secs - start_secs
            if duration < 30:  # Minimum 30 seconds
                continue

            # Clamp to video duration
            end_secs = min(end_secs, video_duration)

            chapters.append({
                "id": f"ch_{i+1}",
                "title": item.get("title", f"Chapter {i+1}")[:30],
                "start": float(start_secs),
                "end": float(end_secs),
                "duration": float(end_secs - start_secs),
                "summary": item.get("summary", "")[:100],
                "keywords": item.get("keywords", [])[:5],
                "confidence": 0.85,
                "selected": False
            })

        return chapters

    except Exception as e:
        print(f"Failed to parse chapter response: {e}")
        return []


def generate_fallback_chapters(segments: list, video_duration: float) -> list:
    """Rule-based fallback: divide video into ~3 minute chapters"""
    chapters = []
    chapter_duration = 180  # 3 minutes
    num_chapters = max(1, int(video_duration / chapter_duration))

    for i in range(num_chapters):
        start = i * chapter_duration
        end = min((i + 1) * chapter_duration, video_duration)

        # Find segments in this range
        chapter_segments = [
            seg for seg in segments
            if seg["start"] >= start and seg["start"] < end
        ]

        # Extract simple keywords from segments
        all_text = " ".join([seg["text"] for seg in chapter_segments])
        keywords = extract_keywords_simple(all_text)

        # Generate simple title from first segment
        first_text = chapter_segments[0]["text"][:30] if chapter_segments else f"Part {i+1}"

        chapters.append({
            "id": f"ch_{i+1}",
            "title": f"Part {i+1}: {first_text[:15]}...",
            "start": float(start),
            "end": float(end),
            "duration": float(end - start),
            "summary": f"Video segment {i+1} of {num_chapters}",
            "keywords": keywords[:5],
            "confidence": 0.5,
            "selected": False
        })

    return chapters


def extract_keywords_simple(text: str) -> list:
    """Extract simple keywords from text (rule-based)"""
    # Common Indonesian/English stopwords to exclude
    stopwords = {
        "yang", "dan", "di", "ini", "itu", "dengan", "untuk", "adalah", "pada",
        "dari", "ke", "ada", "juga", "tidak", "akan", "bisa", "kita", "saya",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between", "under",
    }

    # Clean and tokenize
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())

    # Count word frequencies (excluding stopwords)
    word_counts = {}
    for word in words:
        if word not in stopwords:
            word_counts[word] = word_counts.get(word, 0) + 1

    # Sort by frequency and return top keywords
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:10]]


def smart_chapter_detection(
    segments: list,
    video_duration: float,
    use_ai: bool = True
) -> tuple:
    """
    Hybrid chapter detection.
    Returns (chapters, method_used)
    """
    ai_available = bool(settings.gemini_api_key or settings.openai_api_key)

    if use_ai and ai_available:
        try:
            chapters = analyze_chapters_with_ai(segments, video_duration)
            if chapters and len(chapters) >= 1:
                return chapters, "ai"
            else:
                print("AI chapter detection returned no chapters, falling back to rule-based")
        except Exception as e:
            print(f"AI chapter detection failed: {e}")

    # Fallback to rule-based
    chapters = generate_fallback_chapters(segments, video_duration)
    return chapters, "rule-based"


# =============================================================================
# TRANSLATION FUNCTIONS (New Feature)
# =============================================================================

def translate_subtitles_batch(
    segments: list,
    target_language: str = None,
    batch_size: int = None
) -> list:
    """
    Batch translate subtitles to minimize API calls.
    Processes N subtitles per API call (default 20).
    """
    if not segments:
        return []

    target_lang = target_language or settings.target_language
    batch_sz = batch_size or settings.translation_batch_size

    # Language name mapping
    lang_names = {
        "id": "Indonesian",
        "zh": "Chinese (Simplified)",
        "ja": "Japanese",
        "ko": "Korean",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "pt": "Portuguese",
        "ar": "Arabic",
        "hi": "Hindi",
    }
    lang_name = lang_names.get(target_lang, target_lang)

    translated = []
    total_batches = (len(segments) + batch_sz - 1) // batch_sz

    for batch_idx in range(0, len(segments), batch_sz):
        batch = segments[batch_idx:batch_idx + batch_sz]
        current_batch = (batch_idx // batch_sz) + 1

        print(f"Translating batch {current_batch}/{total_batches}...")

        # Build batch translation prompt
        texts_to_translate = [seg["text"] for seg in batch]

        prompt = f"""Translate these video subtitles to {lang_name}.

Requirements:
- Keep translations natural and conversational (suitable for video captions)
- Maintain technical accuracy
- Be concise and fluent
- Preserve the original meaning

Original texts (numbered):
{chr(10).join([f'{i+1}. {t}' for i, t in enumerate(texts_to_translate)])}

Return ONLY the translations, one per line, numbered to match:
1. [translation]
2. [translation]
..."""

        translations = call_translation_api(prompt, len(texts_to_translate))

        # Merge with original segments
        for i, seg in enumerate(batch):
            translated.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "translation": translations[i] if i < len(translations) else seg["text"]
            })

    return translated


def call_translation_api(prompt: str, expected_count: int) -> list:
    """Call AI API for translation"""
    translations = []

    if settings.gemini_api_key:
        try:
            try:
                from google import genai
                client = genai.Client(api_key=settings.gemini_api_key)
                response = client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents=prompt
                )
                translations = parse_numbered_list(response.text, expected_count)
                if translations:
                    return translations
            except ImportError:
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                translations = parse_numbered_list(response.text, expected_count)
                if translations:
                    return translations
        except Exception as e:
            print(f"Gemini translation error: {e}")

    if settings.openai_api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            translations = parse_numbered_list(
                response.choices[0].message.content,
                expected_count
            )
        except Exception as e:
            print(f"OpenAI translation error: {e}")

    # Fallback: return original texts
    return translations if translations else [""] * expected_count


def parse_numbered_list(text: str, expected_count: int) -> list:
    """Parse numbered list from AI response"""
    lines = text.strip().split('\n')
    results = []

    for line in lines:
        # Match patterns like "1. translation" or "1) translation"
        match = re.match(r'^\d+[\.\)]\s*(.+)$', line.strip())
        if match:
            results.append(match.group(1))

    # Pad with empty strings if needed
    while len(results) < expected_count:
        results.append("")

    return results[:expected_count]


def create_bilingual_srt(
    translated_segments: list,
    output_path: str,
    original_first: bool = True
) -> str:
    """Create bilingual SRT file with both languages"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(translated_segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n")

            if original_first:
                f.write(f"{seg['text']}\n")
                f.write(f"{seg.get('translation', seg['text'])}\n")
            else:
                f.write(f"{seg.get('translation', seg['text'])}\n")
                f.write(f"{seg['text']}\n")

            f.write("\n")

    return output_path


def create_mono_srt(
    segments: list,
    output_path: str,
    use_translation: bool = False
) -> str:
    """Create single-language SRT file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n")

            text = seg.get('translation', seg['text']) if use_translation else seg['text']
            f.write(f"{text}\n\n")

    return output_path


# =============================================================================
# SOCIAL MEDIA CONTENT GENERATION (New Feature)
# =============================================================================

def generate_social_content(chapter: dict, transcript_text: str) -> str:
    """Generate platform-specific social media content."""
    prompt = f"""Based on this video chapter, generate social media content.

Chapter: {chapter['title']}
Duration: {int(chapter['duration'])} seconds
Summary: {chapter['summary']}
Keywords: {', '.join(chapter.get('keywords', []))}

Transcript excerpt:
{transcript_text[:2000]}

Generate content for:

1. TikTok/Reels (15-60 words)
   - Hook in first line
   - 3 key points
   - Call to action
   - 5 hashtags

2. YouTube Shorts Description (50-100 words)
   - Compelling title
   - What viewers will learn
   - 10 hashtags

3. Instagram Caption (100-150 words)
   - Engaging opener
   - Value points
   - Question for engagement
   - 15 hashtags

4. Tweet (280 chars max)
   - Single impactful statement
   - 3 hashtags

Format as Markdown with clear sections."""

    content = ""

    if settings.gemini_api_key:
        try:
            try:
                from google import genai
                client = genai.Client(api_key=settings.gemini_api_key)
                response = client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents=prompt
                )
                content = response.text
            except ImportError:
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                content = response.text
        except Exception as e:
            print(f"Content generation error (Gemini): {e}")

    if not content and settings.openai_api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500
            )
            content = response.choices[0].message.content
        except Exception as e:
            print(f"Content generation error (OpenAI): {e}")

    # Fallback template
    if not content:
        content = f"""# {chapter['title']}

## Quick Summary
{chapter['summary']}

## Keywords
{', '.join(chapter.get('keywords', []))}

## Social Media Templates

### TikTok/Reels
[Auto-generation unavailable - AI API key required]

### YouTube Shorts
[Auto-generation unavailable - AI API key required]

### Instagram
[Auto-generation unavailable - AI API key required]

---
Generated from video chapter: {int(chapter['start'])}s - {int(chapter['end'])}s
"""

    return content


# =============================================================================
# MULTI-OUTPUT FORMAT FUNCTIONS (New Feature)
# =============================================================================

def get_crop_filter(width: int, height: int, face_count: int = None, last_layout: str = "single") -> tuple:
    """
    Face-aware layout decision.
    Returns: (filter_string, layout_used)
    """

    target_w = settings.output_width   # 1080
    target_h = settings.output_height  # 1920
    half_h = target_h // 2

    # --- FACE-BASED DECISION ---
    if face_count is not None:
        if face_count >= 2:
            layout = "split"
        elif face_count == 1:
            layout = "single"
        else:
            layout = last_layout  # fallback kalau kosong
    else:
        # fallback lama (aspect ratio)
        input_ar = width / height
        target_ar = target_w / target_h
        layout = "split" if input_ar > target_ar else "single"

    # --- BUILD FILTER ---
    if layout == "split":
        return (
            f"split[top][bottom];"
            f"[top]scale={target_w}:-2,pad={target_w}:{half_h}:0:(oh-ih)/2:black[top_out];"
            f"[bottom]scale={target_w}:{half_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{half_h}[bottom_out];"
            f"[top_out][bottom_out]vstack",
            "split"
        )

    # SINGLE FACE
    return (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h}",
        "single"
    )

    
# =============================================================================
# FACE DETECTION (FREE, CPU-ONLY)
# =============================================================================

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def detect_face_count(video_path: str, timestamp: float) -> int:
    """
    Detect number of faces at a specific timestamp.
    Return: 0, 1, or 2 (2 = 2 or more)
    """
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        frame_path = tmp.name

    try:
        # Extract frame
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                frame_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )

        img = cv2.imread(frame_path)
        if img is None:
            print(f"DEBUG: Face detection - could not read frame at {timestamp}s", flush=True)
            return 0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # More sensitive face detection for podcast/interview scenarios
        # Use smaller minSize to detect faces that are farther away
        faces = FACE_CASCADE.detectMultiScale(
            gray,
            scaleFactor=1.1,   # More granular scaling (was 1.2)
            minNeighbors=4,    # Slightly lower threshold (was 5)
            minSize=(50, 50),  # Smaller min face size (was 80x80)
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        face_count = len(faces)
        print(f"DEBUG: Face detection at {timestamp:.1f}s - found {face_count} face(s)", flush=True)

        if face_count >= 2:
            return 2
        elif face_count == 1:
            return 1
        return 0

    except Exception as e:
        print(f"DEBUG: Face detection error: {e}", flush=True)
        return 0
    finally:
        if os.path.exists(frame_path):
            os.remove(frame_path)


def generate_clip_raw(
    input_file: str,
    output_file: str,
    start: float,
    duration: float
):
    """Generate clip without subtitles"""
    
    # Simple aspect check (not accurate without passing dimensions, but safe default)
    # Ideally should pass dimensions, but let's try to probe or just use the blur default for now?
    # Actually, we need to update the signature to accept dimensions or probe here.
    # Since we can't easily change signature everywhere without breaking things, let's probe inside if needed.
    
    # Probe input dimensions
    cmd_probe = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", input_file]
    try:
        dim_res = subprocess.run(cmd_probe, capture_output=True, text=True)
        w, h = map(int, dim_res.stdout.strip().split('x'))
    except:
        w, h = 1920, 1080 # Fallback
    
    filter_str, _ = get_crop_filter(w, h)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-ss", str(start),
        "-t", str(duration),
        "-filter_complex", filter_str,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", str(settings.output_crf),
        "-c:a", "aac",
        "-b:a", "128k",
        output_file
    ]
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)


def generate_clip_with_subtitles(
    input_file: str,
    output_file: str,
    srt_file: str,
    start: float,
    duration: float,
    style: dict,
    options: dict = None
):
    """Generate clip with burned-in subtitles"""
    options = options or {}
    print(f"DEBUG: generate_clip_with_subtitles - start={start}, duration={duration}", flush=True)

    # Escape special characters in path for FFmpeg
    escaped_srt = srt_file.replace("\\", "/").replace(":", "\\:")

    # Probe dimensions
    cmd_probe = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", input_file]
    try:
        dim_res = subprocess.run(cmd_probe, capture_output=True, text=True, timeout=30)
        w, h = map(int, dim_res.stdout.strip().split('x'))
        print(f"DEBUG: Video dimensions: {w}x{h}", flush=True)
    except Exception as e:
        print(f"DEBUG: Could not probe dimensions: {e}, using fallback", flush=True)
        w, h = 1920, 1080 # Fallback

    # ---- FACE AWARE ----
    # Sample multiple timestamps for better face detection
    sample_times = [
        start + duration * 0.25,
        start + duration * 0.5,
        start + duration * 0.75
    ]
    face_counts = [detect_face_count(input_file, t) for t in sample_times]
    face_count = max(face_counts)  # Use highest detected count
    print(f"DEBUG: Face detection samples: {face_counts}, using max: {face_count}", flush=True)

    crop_filter, used_layout = get_crop_filter(
        w,
        h,
        face_count=face_count,
        last_layout=options.get("last_layout", "single")
    )
    print(f"DEBUG: Layout selected: {used_layout} (face_count={face_count})", flush=True)

    options["last_layout"] = used_layout

    # Combine crop filter with subtitles
    base_filter = crop_filter + "[v_cropped]"

    final_filter = (
        f"{base_filter};"
        f"[v_cropped]subtitles={escaped_srt}:force_style='{style['style']}',"
        f"eq=contrast=1.05:saturation=1.1"
    )

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-ss", str(start),
        "-t", str(duration),
        "-filter_complex", final_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", str(settings.output_crf),
        "-c:a", "aac",
        "-b:a", "128k",
        "-threads", "2",
        output_file
    ]

    print(f"DEBUG: Running FFmpeg command...", flush=True)
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(f"DEBUG: FFmpeg error: {result.stderr[-500:]}", flush=True)
            raise subprocess.CalledProcessError(result.returncode, ffmpeg_cmd, result.stdout, result.stderr)
        print(f"DEBUG: FFmpeg completed successfully", flush=True)
    except subprocess.TimeoutExpired:
        print(f"DEBUG: FFmpeg timed out after 10 minutes", flush=True)
        raise Exception("FFmpeg processing timed out")


def filter_segments_for_chapter(
    segments: list,
    chapter_start: float,
    chapter_end: float
) -> list:
    """Filter and adjust segments for a specific chapter time range"""
    chapter_segments = []

    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["end"]

        # Check if segment overlaps with chapter
        if seg_start < chapter_end and seg_end > chapter_start:
            # Calculate relative timing
            new_start = max(0, seg_start - chapter_start)
            new_end = min(chapter_end - chapter_start, seg_end - chapter_start)

            if new_end > new_start and (new_end - new_start) >= 0.1:
                chapter_segments.append({
                    "start": new_start,
                    "end": new_end,
                    "text": seg["text"].strip(),
                    "translation": seg.get("translation", "")
                })

    return chapter_segments


def process_single_chapter(
    job_dir: str,
    chapter: dict,
    segments: list,
    options: dict
) -> dict:
    """
    Generate all output formats for a single chapter.
    Returns paths to all generated files.
    """
    import json as json_module

    chapter_id = chapter["id"]
    input_file = os.path.join(job_dir, "input.mp4")

    log_progress(job_dir, f"  📁 Processing chapter: {chapter_id}")
    log_progress(job_dir, f"  ⏱️ Time range: {chapter['start']:.1f}s - {chapter['end']:.1f}s ({chapter['duration']:.1f}s)")

    # Safe filename from chapter title
    safe_title = re.sub(r'[^\w\s-]', '', chapter["title"])[:30].strip().replace(' ', '_')

    # Output paths
    outputs = {
        "clip_raw": os.path.join(job_dir, f"{chapter_id}_raw.mp4"),
        "clip_subtitled": os.path.join(job_dir, f"{chapter_id}_subtitled.mp4"),
        "srt_original": os.path.join(job_dir, f"{chapter_id}.srt"),
        "srt_bilingual": os.path.join(job_dir, f"{chapter_id}_bilingual.srt"),
        "thumbnail": os.path.join(job_dir, f"{chapter_id}_thumb.jpg"),
        "summary": os.path.join(job_dir, f"{chapter_id}_summary.md")
    }

    # Filter segments for this chapter
    log_progress(job_dir, f"  🔍 Filtering segments...")
    chapter_segments = filter_segments_for_chapter(
        segments,
        chapter["start"],
        chapter["end"]
    )
    log_progress(job_dir, f"  ✅ Found {len(chapter_segments)} segments for this chapter")

    # Get caption style
    style = CAPTION_STYLES.get(
        options.get("caption_style", "default"),
        CAPTION_STYLES["default"]
    )
    log_progress(job_dir, f"  🎨 Caption style: {style.get('name', 'Default')}")

    # Apply dynamic splitting if needed
    if style.get("dynamic"):
        log_progress(job_dir, f"  ✂️ Applying dynamic splitting...")
        chapter_segments = split_segments_for_style(chapter_segments, style)
        log_progress(job_dir, f"  ✅ Split into {len(chapter_segments)} segments")

    # 1. Generate original SRT (always)
    log_progress(job_dir, f"  📝 Generating SRT file...")
    create_mono_srt(chapter_segments, outputs["srt_original"])
    log_progress(job_dir, f"  ✅ SRT file created")

    # 2. Translation (if enabled)
    translated_segments = chapter_segments
    if options.get("enable_translation", settings.enable_translation):
        log_progress(job_dir, f"  🌐 Translating subtitles...")
        translated_segments = translate_subtitles_batch(chapter_segments)
        create_bilingual_srt(translated_segments, outputs["srt_bilingual"])
        log_progress(job_dir, f"  ✅ Translation complete")
    else:
        outputs["srt_bilingual"] = None

    # 3. Generate raw clip (no subtitles) - if multi-output enabled
    if options.get("enable_multi_output", settings.enable_multi_output):
        log_progress(job_dir, f"  🎥 Generating raw clip...")
        generate_clip_raw(
            input_file,
            outputs["clip_raw"],
            chapter["start"],
            chapter["duration"]
        )
        log_progress(job_dir, f"  ✅ Raw clip complete")
    else:
        outputs["clip_raw"] = None

    # 4. Generate subtitled clip
    log_progress(job_dir, f"  🎬 Generating subtitled clip (this may take a while)...")
    # Write temp SRT for FFmpeg (with adjusted timing)
    temp_srt = os.path.join(job_dir, f"{chapter_id}_temp.srt")
    if outputs["srt_bilingual"]:
        # Use bilingual if available
        with open(outputs["srt_bilingual"], 'r', encoding='utf-8') as f:
            srt_content = f.read()
        with open(temp_srt, 'w', encoding='utf-8') as f:
            f.write(srt_content)
    else:
        with open(outputs["srt_original"], 'r', encoding='utf-8') as f:
            srt_content = f.read()
        with open(temp_srt, 'w', encoding='utf-8') as f:
            f.write(srt_content)

    generate_clip_with_subtitles(
        input_file,
        outputs["clip_subtitled"],
        temp_srt,
        chapter["start"],
        chapter["duration"],
        style,
        options
    )
    log_progress(job_dir, f"  ✅ Subtitled clip complete")

    # Clean up temp SRT
    if os.path.exists(temp_srt):
        os.remove(temp_srt)

    # ===============================
    # POST-PROCESSING: Smart Reframe
    # ===============================
    if options.get("enable_smart_reframe", settings.enable_smart_reframe):
        log_progress(job_dir, f"  🎯 Applying Smart Reframe (face tracking)...")
        try:
            reframe_input = outputs["clip_subtitled"]
            reframe_output = os.path.join(job_dir, f"{chapter_id}_reframed.mp4")

            success = smart_reframe_video(
                reframe_input,
                reframe_output,
                smoothing=options.get("reframe_smoothing", settings.reframe_smoothing)
            )

            if success and os.path.exists(reframe_output):
                # Replace original with reframed version
                os.replace(reframe_output, outputs["clip_subtitled"])
                log_progress(job_dir, f"  ✅ Smart Reframe applied!")
            else:
                log_progress(job_dir, f"  ⚠️ Smart Reframe skipped (no face detected or error)")
        except Exception as e:
            log_progress(job_dir, f"  ⚠️ Smart Reframe error: {e}")

    # ===============================
    # POST-PROCESSING: Auto Hook
    # ===============================
    if options.get("enable_auto_hook", settings.enable_auto_hook):
        log_progress(job_dir, f"  🎣 Generating Auto Hook text...")
        try:
            # Get transcript text for this chapter
            transcript_text = " ".join([seg["text"] for seg in chapter_segments])

            # Generate hook using AI or rule-based
            hook_text = generate_hook_text_ai(transcript_text)
            if not hook_text:
                hook_text = generate_hook_text_rules(transcript_text)

            if hook_text:
                log_progress(job_dir, f"  📝 Hook: \"{hook_text}\"")

                hook_input = outputs["clip_subtitled"]
                hook_output = os.path.join(job_dir, f"{chapter_id}_hooked.mp4")

                success = add_hook_overlay(
                    hook_input,
                    hook_output,
                    hook_text,
                    duration=options.get("hook_duration", settings.hook_duration),
                    style=options.get("hook_style", settings.hook_style)
                )

                if success and os.path.exists(hook_output):
                    # Replace original with hooked version
                    os.replace(hook_output, outputs["clip_subtitled"])
                    log_progress(job_dir, f"  ✅ Auto Hook applied!")
                else:
                    log_progress(job_dir, f"  ⚠️ Auto Hook overlay failed")
            else:
                log_progress(job_dir, f"  ⚠️ Could not generate hook text")
        except Exception as e:
            log_progress(job_dir, f"  ⚠️ Auto Hook error: {e}")

    # 5. Generate thumbnail
    log_progress(job_dir, f"  🖼️ Generating thumbnail...")
    generate_thumbnail(
        outputs["clip_subtitled"],
        outputs["thumbnail"],
        chapter["duration"] / 2
    )
    log_progress(job_dir, f"  ✅ Thumbnail complete")

    # 6. Generate social content (if enabled)
    if options.get("enable_social_content", settings.enable_social_content):
        log_progress(job_dir, f"  📱 Generating social content...")
        transcript_text = " ".join([seg["text"] for seg in chapter_segments])
        content = generate_social_content(chapter, transcript_text)
        with open(outputs["summary"], 'w', encoding='utf-8') as f:
            f.write(content)
        log_progress(job_dir, f"  ✅ Social content complete")
    else:
        outputs["summary"] = None

    # Build result with all file info
    # Include filename and thumbnail at top level for frontend compatibility
    return {
        "id": chapter_id,
        "title": chapter["title"],
        "duration": chapter["duration"],
        "start": chapter["start"],
        "end": chapter["end"],
        "summary": chapter.get("summary", ""),
        "keywords": chapter.get("keywords", []),
        # Top-level for frontend compatibility (ClipCard expects these)
        "filename": f"{chapter_id}_subtitled.mp4",
        "thumbnail": f"{chapter_id}_thumb.jpg",
        "score": int(chapter.get("confidence", 0.8) * 10),  # Convert confidence to score
        # Detailed file info
        "files": {
            "raw": f"{chapter_id}_raw.mp4" if outputs["clip_raw"] else None,
            "subtitled": f"{chapter_id}_subtitled.mp4",
            "srt": f"{chapter_id}.srt",
            "srt_bilingual": f"{chapter_id}_bilingual.srt" if outputs["srt_bilingual"] else None,
            "thumbnail": f"{chapter_id}_thumb.jpg",
            "summary": f"{chapter_id}_summary.md" if outputs["summary"] else None
        },
        "chapter": chapter
    }


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

        # Download with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                download_cmd = [
                    "yt-dlp",
                    "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]",
                    "--merge-output-format", "mp4",
                    "--no-playlist",  # Prevent downloading entire playlists
                    "--max-filesize", "500M",  # Limit file size
                    "-o", input_file,
                    url
                ]
                subprocess.run(download_cmd, check=True, capture_output=True, timeout=600)
                log_progress(job_dir, "✅ Download complete!")
                break
            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    log_progress(job_dir, f"⚠️ Download timeout, retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    raise Exception("Download timeout after multiple retries")
            except subprocess.CalledProcessError as e:
                if attempt < max_retries - 1:
                    log_progress(job_dir, f"⚠️ Download failed, retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    raise Exception(f"Download failed: {e.stderr.decode() if e.stderr else str(e)}")
        
        # Get video duration and dimensions
        video_width = 1920
        video_height = 1080
        try:
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", 
                        "-of", "default=noprint_wrappers=1:nokey=1", input_file]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            lines = probe_result.stdout.strip().split('\n')
            
            # Very basic parsing, assuming 3 lines (width, height, duration) or similar
            # ffprobe output order can vary, so let's try json output for safety
            json_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration", "-of", "json", input_file]
            json_result = subprocess.run(json_cmd, capture_output=True, text=True)
            import json
            info = json.loads(json_result.stdout)
            stream = info["streams"][0]
            video_width = int(stream.get("width", 1920))
            video_height = int(stream.get("height", 1080))
            # Duration can be in format or stream
            if "duration" in stream:
                 video_duration = float(stream["duration"])
            else:
                 # Fallback to format duration
                 json_format_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", input_file]
                 json_format_result = subprocess.run(json_format_cmd, capture_output=True, text=True)
                 format_info = json.loads(json_format_result.stdout)
                 video_duration = float(format_info["format"]["duration"])
            
            log_progress(job_dir, f"📹 Video info: {video_width}x{video_height}, {int(video_duration//60)}m {int(video_duration%60)}s")
        except Exception as e:
            log_progress(job_dir, f"⚠️ Probe error: {e}, using defaults")
            video_duration = 600
            
        settings.video_width = video_width # Temporary storage (not thread safe but okay for Celery worker logic flow here if passed down)
        options["video_width"] = video_width
        options["video_height"] = video_height
        
        # Step 2: Generate subtitles with Whisper
        self.update_state(state="TRANSCRIBING", meta={"progress": 40})
        log_progress(job_dir, f"🎧 Loading Whisper model ({settings.whisper_model})...")

        import whisper
        import torch

        # Optimize memory usage - use CPU if low RAM, otherwise GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        log_progress(job_dir, f"⚙️ Using device: {device.upper()}")

        model = whisper.load_model(settings.whisper_model, device=device)
        log_progress(job_dir, "🎧 Transcribing audio... (this may take a while)")

        # Transcribe with optimizations
        transcribe_options = {
            "verbose": False,
            "fp16": False,  # Disable FP16 for CPU compatibility
            "compression_ratio_threshold": 2.4,  # Skip low-quality segments
            "no_speech_threshold": 0.6  # Skip silence
        }

        # Only add language if explicitly set (None = auto-detect)
        if settings.whisper_language:
            transcribe_options["language"] = settings.whisper_language
            log_progress(job_dir, f"🌍 Language: {settings.whisper_language}")
        else:
            log_progress(job_dir, "🌍 Language: auto-detect")

        result = model.transcribe(input_file, **transcribe_options)
        
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
            
        # Free up memory (Important for small RAM)
        try:
            del model
            import gc
            gc.collect()
            log_progress(job_dir, "🧹 Freed up memory (unloaded Whisper model)")
        except:
            pass
        
        # --- Apply Text Correction Pipeline ---
        log_progress(job_dir, "🧹 Running text correction (normalizing & slang fix)...")
        use_llm_correction = options.get("use_ai_detection", False) # Reuse flag for now
        segments = correct_text_pipeline(segments, use_llm=use_llm_correction)
        log_progress(job_dir, "✅ Text clean up complete")
        
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
        
        generated_clips = []
        
        # Determine clips to generate
        # If auto_detect is TRUE, generate from suggested_clips (top 3)
        # If auto_detect is FALSE, use the single manual timestamp
        
        clips_to_process = []
        
        if options.get("clip_start") is not None:
             # Manual mode: Single clip
             clips_to_process.append({
                 "start": options["clip_start"],
                 "duration": options.get("clip_duration", settings.clip_duration),
                 "filename": "output.mp4",
                 "score": 0,
                 "id": "manual"
             })
             log_progress(job_dir, f"📍 Processing manual clip at {options['clip_start']}s")
             
        elif options.get("auto_detect", True) and suggested_clips:
            # Auto mode: Top 9 viral clips (like OpusClip)
            max_clips = min(9, len(suggested_clips))
            log_progress(job_dir, f"🚀 Generating top {max_clips} viral clips...")

            for i, clip in enumerate(suggested_clips[:9]):
                clips_to_process.append({
                    "start": clip["start"],
                    "duration": clip["duration"],
                    "filename": f"clip_{i+1}.mp4",
                    "score": clip["score"],
                    "hook": clip["hook"],
                    "id": f"viral_{i+1}"
                })
        else:
            # Fallback default
            clips_to_process.append({
                "start": settings.clip_start,
                "duration": settings.clip_duration,
                "filename": "output.mp4",
                "score": 0,
                "id": "default"
            })
            log_progress(job_dir, f"📍 Processing default clip at {settings.clip_start}s")

        # Get caption style
        style_name = options.get("caption_style", "default")
        style = CAPTION_STYLES.get(style_name, CAPTION_STYLES["default"])
        log_progress(job_dir, f"🎨 Using caption style: {style['name']}")
        
        # Apply dynamic splitting if needed (e.g. for CapCut style)
        processed_segments = segments
        if style.get("dynamic"):
            log_progress(job_dir, "⚡ Applying dynamic segment splitting...")
            processed_segments = split_segments_for_style(segments, style)
            
        # Loop to generate clips
        total_clips = len(clips_to_process)
        
        for idx, clip_info in enumerate(clips_to_process, 1):
            clip_start = clip_info["start"]
            clip_duration = clip_info["duration"]
            output_filename = clip_info["filename"]
            clip_id = clip_info["id"]
            
            log_progress(job_dir, f"🎬 [{idx}/{total_clips}] Processing clip: {output_filename} ({int(clip_start)}s)")
            
            current_output = os.path.join(job_dir, output_filename)
            clip_srt_file = os.path.join(job_dir, f"subs_{clip_id}.srt")
            
            # Create adjusted SRT for this specific clip
            # Note: We need to write this to a file for FFmpeg to use
            
            # Filter segments for this clip
            clip_segments = []
            clip_end = clip_start + clip_duration

            for seg in processed_segments:
                 # Check overlap (more lenient)
                 seg_start = seg["start"]
                 seg_end = seg["end"]

                 # Include segment if ANY part overlaps with clip time range
                 if seg_start < clip_end and seg_end > clip_start:
                     # Calculate relative timing
                     new_start = max(0, seg_start - clip_start)
                     new_end = min(clip_duration, seg_end - clip_start)

                     # Ensure valid duration (at least 0.1 seconds)
                     if new_end > new_start and (new_end - new_start) >= 0.1:
                         clip_segments.append({
                             "start": new_start,
                             "end": new_end,
                             "text": seg["text"].strip()
                         })

            # Debug: log how many segments found
            log_progress(job_dir, f"   Found {len(clip_segments)} subtitle segments for this clip")

            # Fallback: if no segments found, try to find nearest segments
            if len(clip_segments) == 0:
                log_progress(job_dir, f"   ⚠️ No subtitles found! Searching for nearest segments...")
                # Find segments within 5 seconds before/after clip
                for seg in processed_segments:
                    if abs(seg["start"] - clip_start) <= 5:
                        new_start = max(0, seg["start"] - clip_start)
                        new_end = min(clip_duration, seg["end"] - clip_start)
                        if new_end > 0:
                            clip_segments.append({
                                "start": max(0, new_start),
                                "end": new_end,
                                "text": seg["text"].strip()
                            })
                            log_progress(job_dir, f"   ✅ Added fallback segment: {seg['text'][:50]}")

            # Write unique SRT file for this clip
            with open(clip_srt_file, "w", encoding="utf-8") as f:
                if len(clip_segments) == 0:
                    # Ultimate fallback: add a placeholder subtitle
                    log_progress(job_dir, f"   ⚠️ Still no subtitles, using placeholder")
                    f.write(f"1\n{format_timestamp(0)} --> {format_timestamp(clip_duration)}\n[Viral Moment]\n\n")
                else:
                    for i, seg in enumerate(clip_segments, 1):
                        start = format_timestamp(seg["start"])
                        end = format_timestamp(seg["end"])
                        text = seg["text"].strip()
                        if text:  # Only write non-empty text
                            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

            # Probe clip dimensions (or use global if passed)
            w, h = options.get("video_width", 1920), options.get("video_height", 1080)

            crop_filter, _ = get_crop_filter(w, h)
            base_filter = crop_filter + "[v_cropped]"
            
            final_filter = (
                f"{base_filter};"
                f"[v_cropped]subtitles={clip_srt_file}:force_style='{style['style']}',"
                f"eq=contrast=1.05:saturation=1.1"
            )

            # FFmpeg Command
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", input_file,
                "-ss", str(clip_start),
                "-t", str(clip_duration),
                "-filter_complex", final_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", str(settings.output_crf),
                "-c:a", "aac",
                "-b:a", "128k",
                current_output
            ]
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

            # Generate thumbnail from the middle of the clip
            thumbnail_filename = f"thumb_{clip_id}.jpg"
            thumbnail_path = os.path.join(job_dir, thumbnail_filename)
            thumbnail_timestamp = clip_duration / 2  # Middle of the clip

            log_progress(job_dir, f"📸 Generating thumbnail...")
            generate_thumbnail(current_output, thumbnail_path, thumbnail_timestamp)

            generated_clips.append({
                "filename": output_filename,
                "thumbnail": thumbnail_filename if os.path.exists(thumbnail_path) else None,
                "score": clip_info.get("score", 0),
                "hook": clip_info.get("hook", "Clip"),
                "path": current_output
            })
        
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
            "clips": generated_clips, # Updated to return list of clips
            "output_file": generated_clips[0]["path"] if generated_clips else None, # Backwards compatibility
            "suggested_clips": suggested_clips[:5]
        }
        
    except Exception as e:
        log_progress(job_dir, f"❌ Error: {str(e)}")
        self.update_state(state="FAILED", meta={"error": str(e)})
        raise




# --- Text Processing Pipeline ---

class TextProcessor:
    """Handles text normalization and correction"""
    
    # Common Indonesian Slang Dictionary
    SLANG_DICT = {
        r"\bgak\b": "tidak",
        r"\bnggak\b": "tidak",
        r"\bga\b": "tidak",
        r"\btak\b": "tidak",
        r"\bgk\b": "tidak",
        r"\byg\b": "yang",
        r"\bak\b": "aku",
        r"\baqu\b": "aku",
        r"\bgw\b": "gue",
        r"\blu\b": "lo",
        r"\budh\b": "sudah",
        r"\bdah\b": "sudah",
        r"\bblm\b": "belum",
        r"\bkrn\b": "karena",
        r"\bkalo\b": "kalau",
        r"\bkl\b": "kalau",
        r"\bjd\b": "jadi",
        r"\bjg\b": "juga",
        r"\bbr\b": "baru",
        r"\bspt\b": "seperti",
        r"\bgmn\b": "gimana",
        r"\bpd\b": "pada",
        r"\bdlm\b": "dalam",
        r"\bdr\b": "dari",
        r"\butk\b": "untuk",
        r"\bny\b": "nya",
        r"\bbgt\b": "banget",
        r"\baja\b": "saja",
        r"\baj\b": "saja",
        r"\bsama\b": "sama",
        r"\bsm\b": "sama",
        r"\bthx\b": "makasih",
        r"\bmkasih\b": "makasih",
        r"\bjan\b": "jangan",
        r"\bjgn\b": "jangan",
        r"\btdk\b": "tidak",
        # Specific Phonetic Fixes (Whisper Hallucinations)
        r"\bmasyumis\b": "masih bisa",
        r"\bpisot\b": "episode",
        r"\bcukali\b": "lucu kali",
        r"\bcukam\b": "cuma",
        r"\bkarus\b": "kadang",
        r"\byonobak\b": "yono bakri",
        r"\bayonobakri\b": "yono bakri",
        r"\bdirilus\b": "diri lu",
        r"\bresulusinya\b": "resolusinya",
    }

    @staticmethod
    def normalize(text: str) -> str:
        """Basic normalization: trim, lowercase first char if needed"""
        if not text:
            return ""
        text = text.strip()
        # Ensure only one space between words
        text = re.sub(r'\s+', ' ', text)
        return text

    @staticmethod
    def correct_slang(text: str) -> str:
        """Rule-based replacement of slang words"""
        if not text:
            return ""
        
        # Preserve original case for non-slang words? 
        # For simple subtitle correction, lowercase comparison is safer
        # but we want to keep capitalization for names. 
        # So we use regex with ignore case flag for matching.
        
        corrected = text
        for pattern, replacement in TextProcessor.SLANG_DICT.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
            
        # Fix common punctuation issues
        corrected = re.sub(r'\s+([,.?!])', r'\1', corrected) # Remove space before punct
        
        return corrected

    @staticmethod
    def llm_cleanup(text_batch: list, api_key: str = None, provider: str = "gemini") -> list:
        """
        Optional: Send valid sentences to LLM for context-aware correction.
        Not implemented fully to save tokens, but structure is here.
        """
        if not api_key:
            return text_batch
            
        # TODO: Implement batch LLM correction
        return text_batch


def correct_text_pipeline(segments: list, use_llm: bool = False) -> list:
    """
    Run full text processing pipeline on segments.
    """
    processed = []
    
    for seg in segments:
        text = seg["text"]
        
        # 1. Normalize
        text = TextProcessor.normalize(text)
        
        # 2. Rule-based Correction
        text = TextProcessor.correct_slang(text)
        
        # 3. Add to list
        processed.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": text
        })
        
    # 4. LLM Cleanup (Batch) - Optional
    if use_llm and (settings.gemini_api_key or settings.openai_api_key):
        # Implementation for future: splitting into batches and sending to API
        pass
        
    return processed


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_thumbnail(video_path: str, thumbnail_path: str, timestamp: float = 0):
    """Generate a thumbnail from video at specific timestamp"""
    try:
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-vf", "scale=320:-1",  # 320px width, maintain aspect ratio
            "-q:v", "2",  # High quality
            thumbnail_path
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Failed to generate thumbnail: {e}")
        return False


def split_segments_for_style(segments: list, style: dict) -> list:
    """
    Split segments into shorter chunks for dynamic/CapCut style.
    Aim for 2-4 words per chunk for better readability.
    """
    # Only split if style is dynamic
    if not style.get("dynamic"):
        return segments

    new_segments = []

    for seg in segments:
        text = seg["text"].strip()
        if not text:  # Skip empty text
            continue

        words = text.split()

        # If segment is already short (1-3 words), keep it
        if len(words) <= 3:
            new_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": text
            })
            continue

        # Calculate duration per word
        duration = seg["end"] - seg["start"]
        word_duration = duration / len(words) if words else 0

        # Split into chunks of 2-3 words (CapCut style)
        chunk_size = 3
        current_time = seg["start"]

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunk_duration = len(chunk_words) * word_duration

            # Ensure minimum duration of 0.2 seconds
            if chunk_duration < 0.2:
                chunk_duration = 0.2

            new_segments.append({
                "start": current_time,
                "end": min(current_time + chunk_duration, seg["end"]),
                "text": chunk_text.upper()  # CapCut uses UPPERCASE
            })

            current_time += chunk_duration

    return new_segments


# =============================================================================
# TWO-PHASE CELERY TASKS (New Feature)
# =============================================================================

@celery_app.task(bind=True)
def process_video_phase1(self, job_id: str, url: str, options: dict = None):
    """
    Phase 1: Download + Transcribe + Generate Chapters
    Stops at 'chapters_ready' state for user selection.
    """
    import json as json_module

    options = options or {}

    # Paths
    data_dir = settings.data_dir
    job_dir = os.path.join(data_dir, "jobs", job_id)
    os.makedirs(job_dir, exist_ok=True)

    input_file = os.path.join(job_dir, "input.mp4")
    srt_file = os.path.join(job_dir, "input.srt")

    try:
        # Step 1: Download video
        log_progress(job_dir, "🚀 Starting Phase 1: Download & Analyze...")
        log_progress(job_dir, f"📎 URL: {url}")
        self.update_state(state="DOWNLOADING", meta={"progress": 10})
        log_progress(job_dir, "⬇️ Downloading video from YouTube...")

        # Download with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                download_cmd = [
                    "yt-dlp",
                    "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]",
                    "--merge-output-format", "mp4",
                    "--no-playlist",
                    "--max-filesize", "500M",
                    "-o", input_file,
                    url
                ]
                subprocess.run(download_cmd, check=True, capture_output=True, timeout=600)
                log_progress(job_dir, "✅ Download complete!")
                break
            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    log_progress(job_dir, f"⚠️ Download timeout, retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    raise Exception("Download timeout after multiple retries")
            except subprocess.CalledProcessError as e:
                if attempt < max_retries - 1:
                    log_progress(job_dir, f"⚠️ Download failed, retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    raise Exception(f"Download failed: {e.stderr.decode() if e.stderr else str(e)}")

        # Get video duration
        video_duration = 0
        try:
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", input_file]
            duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            video_duration = float(duration_result.stdout.strip())
            log_progress(job_dir, f"📹 Video duration: {int(video_duration//60)}m {int(video_duration%60)}s")
        except:
            video_duration = 600  # Default 10 minutes if probe fails

        # Step 2: Generate subtitles with Whisper
        self.update_state(state="TRANSCRIBING", meta={"progress": 30})
        log_progress(job_dir, f"🎧 Loading Whisper model ({settings.whisper_model})...")

        import whisper
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        log_progress(job_dir, f"⚙️ Using device: {device.upper()}")

        model = whisper.load_model(settings.whisper_model, device=device)
        log_progress(job_dir, "🎧 Transcribing audio... (this may take a while)")

        transcribe_options = {
            "verbose": False,
            "fp16": False,
            "compression_ratio_threshold": 2.4,
            "no_speech_threshold": 0.6
        }

        if settings.whisper_language:
            transcribe_options["language"] = settings.whisper_language
            log_progress(job_dir, f"🌍 Language: {settings.whisper_language}")
        else:
            log_progress(job_dir, "🌍 Language: auto-detect")

        result = model.transcribe(input_file, **transcribe_options)
        segments = result["segments"]
        log_progress(job_dir, f"📝 Found {len(segments)} subtitle segments")

        # Write SRT file
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

        # Free up memory
        try:
            del model
            import gc
            gc.collect()
            log_progress(job_dir, "🧹 Freed up memory (unloaded Whisper model)")
        except:
            pass

        # Apply text correction
        log_progress(job_dir, "🧹 Running text correction...")
        use_llm_correction = options.get("use_ai_detection", False)
        segments = correct_text_pipeline(segments, use_llm=use_llm_correction)
        log_progress(job_dir, "✅ Transcription complete!")

        # Step 3: Generate Chapters (NEW)
        self.update_state(state="ANALYZING", meta={"progress": 50})
        log_progress(job_dir, "🧠 Analyzing video for chapters...")

        use_ai = options.get("use_ai_detection", True)
        chapters, method = smart_chapter_detection(segments, video_duration, use_ai)

        if method == "ai":
            log_progress(job_dir, f"🤖 AI-powered chapter analysis: Found {len(chapters)} chapters")
        else:
            log_progress(job_dir, f"📊 Rule-based chapter analysis: Found {len(chapters)} chapters")

        # Log chapter preview
        log_progress(job_dir, "📚 Chapters detected:")
        for ch in chapters[:5]:
            start_str = f"{int(ch['start']//60):02d}:{int(ch['start']%60):02d}"
            end_str = f"{int(ch['end']//60):02d}:{int(ch['end']%60):02d}"
            log_progress(job_dir, f"   [{start_str} - {end_str}] {ch['title']}")

        if len(chapters) > 5:
            log_progress(job_dir, f"   ... and {len(chapters) - 5} more chapters")

        # Save chapters for user selection
        chapters_file = os.path.join(job_dir, "chapters.json")
        with open(chapters_file, "w", encoding="utf-8") as f:
            json_module.dump(chapters, f, indent=2, ensure_ascii=False)

        # Save segments for later use
        segments_file = os.path.join(job_dir, "segments.json")
        with open(segments_file, "w", encoding="utf-8") as f:
            json_module.dump(segments, f, indent=2, ensure_ascii=False)

        # Save video duration
        metadata_file = os.path.join(job_dir, "metadata.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json_module.dump({
                "video_duration": video_duration,
                "segment_count": len(segments),
                "chapter_count": len(chapters),
                "detection_method": method
            }, f, indent=2)

        self.update_state(state="CHAPTERS_READY", meta={
            "progress": 60,
            "chapters": chapters,
            "video_duration": video_duration
        })

        log_progress(job_dir, "✅ Phase 1 complete! Waiting for chapter selection...")

        return {
            "status": "chapters_ready",
            "chapters": chapters,
            "video_duration": video_duration,
            "segment_count": len(segments),
            "detection_method": method
        }

    except Exception as e:
        log_progress(job_dir, f"❌ Error: {str(e)}")
        self.update_state(state="FAILED", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, time_limit=3600, soft_time_limit=3500)
def process_selected_chapters(self, job_id: str, chapter_ids: list, options: dict = None):
    """
    Phase 2: Process only the selected chapters.
    Generates clips with all output formats.
    """
    import json as json_module
    import traceback

    options = options or {}

    data_dir = settings.data_dir
    job_dir = os.path.join(data_dir, "jobs", job_id)

    try:
        print(f"DEBUG: Starting process_selected_chapters for {job_id}", flush=True)
        log_progress(job_dir, "🚀 Starting Phase 2: Processing selected chapters...")
        log_progress(job_dir, f"📋 Selected chapters: {', '.join(chapter_ids)}")
        log_progress(job_dir, f"📂 Job directory: {job_dir}")

        # Load saved data
        chapters_file = os.path.join(job_dir, "chapters.json")
        segments_file = os.path.join(job_dir, "segments.json")

        log_progress(job_dir, f"📖 Loading chapters from: {chapters_file}")
        if not os.path.exists(chapters_file):
            raise Exception(f"Chapters file not found: {chapters_file}")

        with open(chapters_file, "r", encoding="utf-8") as f:
            all_chapters = json_module.load(f)
        log_progress(job_dir, f"✅ Loaded {len(all_chapters)} chapters")

        log_progress(job_dir, f"📖 Loading segments from: {segments_file}")
        if not os.path.exists(segments_file):
            raise Exception(f"Segments file not found: {segments_file}")

        with open(segments_file, "r", encoding="utf-8") as f:
            segments = json_module.load(f)
        log_progress(job_dir, f"✅ Loaded {len(segments)} segments")

        # Filter selected chapters
        selected = [ch for ch in all_chapters if ch["id"] in chapter_ids]

        if not selected:
            raise Exception("No valid chapters selected")

        log_progress(job_dir, f"🎬 Processing {len(selected)} chapter(s)...")

        generated_clips = []
        total = len(selected)

        for idx, chapter in enumerate(selected, 1):
            log_progress(job_dir, f"")
            log_progress(job_dir, f"🎬 [{idx}/{total}] Processing: {chapter['title']}")
            log_progress(job_dir, f"   Duration: {int(chapter['duration'])}s")

            self.update_state(state="PROCESSING", meta={
                "progress": 60 + int(35 * idx / total),
                "current_chapter": chapter["title"],
                "current_index": idx,
                "total_chapters": total
            })

            # Process this chapter (generate all output formats)
            clip_data = process_single_chapter(
                job_dir,
                chapter,
                segments,
                options
            )

            generated_clips.append(clip_data)
            log_progress(job_dir, f"   ✅ Chapter {idx} complete!")

        # Save generated clips info
        clips_file = os.path.join(job_dir, "clips.json")
        with open(clips_file, "w", encoding="utf-8") as f:
            json_module.dump(generated_clips, f, indent=2, ensure_ascii=False)

        self.update_state(state="COMPLETED", meta={"progress": 100})

        log_progress(job_dir, "")
        log_progress(job_dir, "🎉 All chapters processed successfully!")
        log_progress(job_dir, f"📁 Output files in: {job_dir}")

        return {
            "status": "completed",
            "clips": generated_clips,
            "total_clips": len(generated_clips)
        }

    except Exception as e:
        log_progress(job_dir, f"❌ Error: {str(e)}")
        self.update_state(state="FAILED", meta={"error": str(e)})
        raise
