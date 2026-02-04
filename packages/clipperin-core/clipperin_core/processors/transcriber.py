"""Audio transcription using Whisper."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from clipperin_core.models.config import WhisperModel


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""

    text: str
    segments: list[dict]
    language: str
    duration: float
    words: list[dict] = None

    @classmethod
    def from_whisper_result(cls, result: dict) -> "TranscriptionResult":
        """Create from Whisper JSON output."""
        segments = result.get("segments", [])
        words = []
        for seg in segments:
            if "words" in seg:
                words.extend(seg["words"])

        return cls(
            text=result.get("text", ""),
            segments=segments,
            language=result.get("language", "en"),
            duration=result.get("segments", [{}])[-1].get("end", 0) if segments else 0,
            words=words if words else None,
        )


class AudioTranscriber:
    """
    Transcribe audio using OpenAI Whisper.

    Supports local models for offline processing.
    """

    def __init__(
        self,
        model: WhisperModel = WhisperModel.BASE,
        language: Optional[str] = None,
        device: str = "cpu",
    ):
        self.model = model
        self.language = language
        self.device = device
        self._model_instance = None

    def _load_model(self):
        """Lazy-load the Whisper model."""
        if self._model_instance is None:
            try:
                import whisper
                self._model_instance = whisper.load_model(self.model.value, device=self.device)
            except ImportError:
                raise RuntimeError("Whisper is not installed. Run: pip install openai-whisper")

    def transcribe(
        self,
        audio_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for transcription progress

        Returns:
            TranscriptionResult with text and segments
        """
        self._load_model()

        # Use whisper CLI for more reliable output
        # Whisper outputs: filename.json (same basename, different extension)
        output_path = audio_path.with_suffix(".json")

        cmd = [
            "whisper",
            str(audio_path),
            "--model", self.model.value,
            "--output_format", "json",
            "--output_dir", str(audio_path.parent),
        ]

        if self.language:
            cmd.extend(["--language", self.language])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Debug: list files in output directory
            import os
            json_files = [f for f in os.listdir(audio_path.parent) if f.endswith('.json') and 'chapters' not in f]
            if not output_path.exists():
                # Try to find any JSON file with matching stem
                for jf in json_files:
                    jp = audio_path.parent / jf
                    if jp.stem == audio_path.stem:
                        output_path = jp
                        break

            # Debug output
            import sys
            print(f"[DEBUG] audio_path: {audio_path}", file=sys.stderr)
            print(f"[DEBUG] output_path: {output_path}", file=sys.stderr)
            print(f"[DEBUG] output_path.exists(): {output_path.exists()}", file=sys.stderr)
            print(f"[DEBUG] json_files: {json_files}", file=sys.stderr)
            print(f"[DEBUG] stdout length: {len(result.stdout)}", file=sys.stderr)
            print(f"[DEBUG] stderr preview: {result.stderr[:200]}", file=sys.stderr)

            # Read the JSON output
            if output_path.exists():
                with open(output_path) as f:
                    whisper_result = json.load(f)
                return TranscriptionResult.from_whisper_result(whisper_result)

            # Fallback: parse from stdout
            if result.stdout:
                print("[DEBUG] Using stdout fallback", file=sys.stderr)
                return self._parse_cli_output(result.stdout)

            # If JSON doesn't exist and no stdout, raise error
            raise RuntimeError(
                f"Transcription failed: No output generated. "
                f"Expected JSON at: {output_path} "
                f"Found JSON files: {json_files} "
                f"stderr: {result.stderr[:500] if result.stderr else 'empty'}"
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Transcription failed with code {e.returncode}. "
                f"stderr: {e.stderr[:500] if e.stderr else 'empty'}"
            ) from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse transcription JSON: {e}") from e

    def transcribe_with_timestamps(
        self,
        audio_path: Path,
    ) -> list[dict]:
        """
        Transcribe and return word-level timestamps.

        Args:
            audio_path: Path to audio file

        Returns:
            List of word entries with start, end, and word
        """
        result = self.transcribe(audio_path)
        words = []

        if result.words:
            return result.words

        # Fallback: split segments into words
        for seg in result.segments:
            text = seg.get("text", "").strip()
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            duration = end - start
            word_list = text.split()
            if word_list:
                word_duration = duration / len(word_list)
                for i, word in enumerate(word_list):
                    words.append({
                        "word": word,
                        "start": start + (i * word_duration),
                        "end": start + ((i + 1) * word_duration),
                    })

        return words

    def _parse_cli_output(self, output: str) -> TranscriptionResult:
        """Parse Whisper CLI output."""
        import re

        segments = []
        for match in re.finditer(r"\[(\d+:\d+\.\d+) --> (\d+:\d+\.\d+)\]\s+(.+)", output):
            start = self._parse_timestamp(match.group(1))
            end = self._parse_timestamp(match.group(2))
            text = match.group(3).strip()
            if text:
                segments.append({"start": start, "end": end, "text": text})

        full_text = " ".join(s["text"] for s in segments)
        duration = segments[-1]["end"] if segments else 0

        return TranscriptionResult(
            text=full_text,
            segments=segments,
            language=self.language or "en",
            duration=duration,
        )

    def _parse_timestamp(self, ts: str) -> float:
        """Parse timestamp string (MM:SS.ms) to seconds."""
        parts = ts.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            return float(minutes) * 60 + float(seconds)
        return 0.0

    def to_srt(self, result: TranscriptionResult, output_path: Path) -> Path:
        """
        Convert transcription to SRT format.

        Args:
            result: Transcription result
            output_path: Output SRT file path

        Returns:
            Path to the SRT file
        """
        with open(output_path, "w") as f:
            for i, seg in enumerate(result.segments, 1):
                start = self._format_srt_time(seg["start"])
                end = self._format_srt_time(seg["end"])
                text = seg.get("text", "").strip()

                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")

        return output_path

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def is_available(self) -> bool:
        """Check if Whisper is available."""
        try:
            import whisper
            return True
        except ImportError:
            return False
