"""Caption renderer for creating stylized subtitles."""

import re
import subprocess
from pathlib import Path
from typing import Optional

from clipper_core.models.config import CaptionStyle


class CaptionRenderer:
    """
    Render captions with various styles.

    Supports multiple animation types and visual styles.
    """

    def __init__(self, default_style: Optional[CaptionStyle] = None):
        self.default_style = default_style or CaptionStyle.get_default_styles()[0]

    def render_ass(
        self,
        srt_path: Path,
        output_path: Path,
        style: Optional[CaptionStyle] = None,
    ) -> Path:
        """
        Convert SRT to ASS with custom styling.

        Args:
            srt_path: Input SRT file
            output_path: Output ASS file
            style: Caption style to apply

        Returns:
            Path to the ASS file
        """
        style = style or self.default_style

        # Parse SRT
        subtitles = self._parse_srt(srt_path)

        # Write ASS with styling
        with open(output_path, "w") as f:
            # ASS header
            f.write("[Script Info]\n")
            f.write("ScriptType: v4.00+\n")
            f.write(f"PlayResX: 1920\n")
            f.write(f"PlayResY: 1920\n")
            f.write(f"Aspect Ratio: {style.max_width}:100\n")
            f.write(f"Collisions: Normal\n")
            f.write(f"WrapStyle: 2\n")
            f.write(f"ScaledBorderAndShadow: yes\n")
            f.write(f"YCbCr Matrix: TV.709\n\n")

            # Styles
            f.write("[V4+ Styles]\n")
            f.write(
                f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                f"OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                f"ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                f"Alignment, MarginL, MarginR, MarginV, Encoding\n"
            )
            f.write(self._format_style(style))
            f.write("\n\n")

            # Events
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for sub in subtitles:
                f.write(self._format_ass_event(sub, style))

        return output_path

    def _parse_srt(self, srt_path: Path) -> list[dict]:
        """Parse SRT file into list of subtitle entries."""
        with open(srt_path) as f:
            content = f.read()

        # Split by double newlines
        blocks = re.split(r'\n\s*\n', content.strip())
        subtitles = []

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # Parse timestamp line: "00:00:00,000 --> 00:00:05,000"
                time_match = re.search(
                    r'(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)',
                    lines[1]
                )
                if time_match:
                    start_h, start_m, start_s, start_ms = map(int, time_match.group(1, 2, 3, 4))
                    end_h, end_m, end_s, end_ms = map(int, time_match.group(5, 6, 7, 8))

                    start = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
                    end = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000

                    text = '\n'.join(lines[2:])

                    subtitles.append({
                        "start": start,
                        "end": end,
                        "text": text,
                    })

        return subtitles

    def _format_style(self, style: CaptionStyle) -> str:
        """Format a CaptionStyle as ASS Style definition."""
        # Convert colors to ASS format (BBGGRR)
        primary = self._hex_to_ass(style.font_color) if style.font_color.startswith("#") else "&H00FFFFFF"
        outline = self._hex_to_ass(style.outline_color) if style.outline_color.startswith("#") else "&H00000000"

        # Position alignment: 1=bottom-left, 2=bottom-center, 3=bottom-right,
        #                     7=top-left, 8=top-center, 9=top-right
        match style.position:
            case "top":
                alignment = 8
            case "middle":
                alignment = 5
            case _:
                alignment = 2

        return (
            f"Style: Default,{style.font_name},{style.font_size},"
            f"{primary},&H00FFFFFF,{outline},&H80000000,"
            f"{-1},0,0,0,100,100,0,0,1,{style.outline},0,"
            f"{alignment},10,10,20,1\n"
        )

    def _format_ass_event(self, sub: dict, style: CaptionStyle) -> str:
        """Format a subtitle as ASS event."""
        start = self._seconds_to_ass_time(sub["start"])
        end = self._seconds_to_ass_time(sub["end"])

        # Apply animation if specified
        text = sub["text"]
        if style.animation == "pop":
            # Add pop effect using \t tags
            text = f"{{\\t(0,200,\\fsc120)\\t(200,400,\\fsc100)}}{text}"
        elif style.animation == "typewriter":
            # Typewriter effect using \k tags (karaoke timing)
            duration = sub["end"] - sub["start"]
            chars = len(re.sub(r'<[^>]+>', '', text))
            cs_per_char = int((duration * 10) / chars) if chars > 0 else 10
            karaoke_text = ""
            for char in text:
                if char == " ":
                    karaoke_text += f"\\k{cs_per_char} "
                else:
                    karaoke_text += f"\\k{cs_per_char}{char}"
            text = f"{{\\K{karaoke_text}}}"

        # Clean up newlines for ASS
        text = text.replace('\n', '\\N')

        return f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS timestamp (H:MM:SS.CC)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    def _hex_to_ass(self, hex_color: str) -> str:
        """Convert hex color to ASS format (BBGGRR)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            # Convert RGB to BGR
            bgr = hex_color[4:6] + hex_color[2:4] + hex_color[0:2]
            return f"&H00{bgr.upper()}"
        return "&H00FFFFFF"

    def word_level_segments(
        self,
        transcription: list[dict],
        max_chars: int = 15,
        max_duration: float = 3.0,
    ) -> list[dict]:
        """
        Group word-level timestamps into subtitle segments.

        Args:
            transcription: Word-level transcription with start/end times
            max_chars: Maximum characters per segment
            max_duration: Maximum duration per segment

        Returns:
            List of subtitle segments
        """
        segments = []
        current_segment = []
        current_start = None

        for word in transcription:
            word_text = word.get("word", "").strip()
            if not word_text:
                continue

            if current_start is None:
                current_start = word.get("start", 0)

            current_segment.append(word_text)
            current_text = " ".join(current_segment)
            current_end = word.get("end", current_start)

            # Check if we should end the segment
            if (
                len(current_text) >= max_chars
                or (current_end - current_start) >= max_duration
                or word_text.endswith((".", "!", "?", ","))
            ):
                segments.append({
                    "start": current_start,
                    "end": current_end,
                    "text": current_text,
                })
                current_segment = []
                current_start = None

        # Handle remaining words
        if current_segment and current_start is not None:
            segments.append({
                "start": current_start,
                "end": transcription[-1].get("end", current_start),
                "text": " ".join(current_segment),
            })

        return segments

    def create_word_level_srt(
        self,
        words: list[dict],
        output_path: Path,
    ) -> Path:
        """
        Create SRT file from word-level timestamps.

        Args:
            words: List of word entries with start, end, word
            output_path: Output SRT file path

        Returns:
            Path to the SRT file
        """
        segments = self.word_level_segments(words)

        with open(output_path, "w") as f:
            for i, seg in enumerate(segments, 1):
                start = self._seconds_to_srt_time(seg["start"])
                end = self._seconds_to_srt_time(seg["end"])
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{seg['text']}\n\n")

        return output_path

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
