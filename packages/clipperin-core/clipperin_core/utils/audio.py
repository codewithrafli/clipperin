"""Audio utilities."""

import subprocess
from pathlib import Path


def extract_audio(
    video_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
) -> bool:
    """
    Extract audio from video file.

    Args:
        video_path: Input video path
        output_path: Output audio path
        sample_rate: Audio sample rate (default 16000 for Whisper)

    Returns:
        True if successful
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path.exists()
    except subprocess.CalledProcessError:
        return False


def get_audio_info(audio_path: Path) -> dict:
    """
    Get audio file information.

    Args:
        audio_path: Path to audio file

    Returns:
        Dict with duration, sample_rate, channels
    """
    import json

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "stream=duration,sample_rate,channels,codec_name",
        "-of", "json",
        str(audio_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        stream = data.get("streams", [{}])[0]
        return {
            "duration": float(stream.get("duration", 0)),
            "sample_rate": int(stream.get("sample_rate", 44100)),
            "channels": int(stream.get("channels", 2)),
            "codec": stream.get("codec_name", "aac"),
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, IndexError):
        return {}


def normalize_audio(
    input_path: Path,
    output_path: Path,
    target_level: float = -16.0,
) -> bool:
    """
    Normalize audio to target loudness level.

    Args:
        input_path: Input audio path
        output_path: Output audio path
        target_level: Target LUFS level (default -16 for EBU R128)

    Returns:
        True if successful
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-af", f"loudnorm=I={target_level}:TP=-1.5:LRA=11",
        "-ar", "16000",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path.exists()
    except subprocess.CalledProcessError:
        return False


def convert_to_mp3(
    input_path: Path,
    output_path: Path,
    bitrate: str = "128k",
) -> bool:
    """
    Convert audio to MP3 format.

    Args:
        input_path: Input audio path
        output_path: Output MP3 path
        bitrate: MP3 bitrate

    Returns:
        True if successful
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path.exists()
    except subprocess.CalledProcessError:
        return False
