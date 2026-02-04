"""Content analyzer using AI providers."""

import json
import re
from typing import Optional
from uuid import uuid4

from clipperin_core.ai.base import AIClient
from clipperin_core.models.config import AIProviderType
from clipperin_core.models.job import Chapter


class ContentAnalyzer:
    """
    Analyze video content to extract chapters and highlights.

    Supports multiple AI providers with fallback to rule-based analysis.
    """

    def __init__(self, ai_client: Optional[AIClient] = None):
        self.ai_client = ai_client

    def analyze_chapters(
        self,
        transcription: str,
        duration: float,
        use_ai: bool = True,
        video_info: Optional[dict] = None,
    ) -> list[Chapter]:
        """
        Analyze transcription to extract chapters.

        Args:
            transcription: Full transcription text
            duration: Total video duration in seconds
            use_ai: Whether to use AI or rule-based analysis
            video_info: Optional video metadata

        Returns:
            List of detected chapters
        """
        if use_ai and self.ai_client and self.ai_client.is_configured():
            return self._ai_analyze(transcription, duration, video_info)
        return self._rule_based_analyze(transcription, duration)

    def _ai_analyze(
        self,
        transcription: str,
        duration: float,
        video_info: Optional[dict] = None,
    ) -> list[Chapter]:
        """Use AI to analyze content."""
        prompt = self.ai_client.format_chapters_prompt(transcription, video_info)

        response = self.ai_client.generate(prompt, json_mode=True)

        if not self.ai_client.validate_response(response):
            return self._rule_based_analyze(transcription, duration)

        parsed = self.ai_client.parse_json_response(response.content)
        if not parsed:
            return self._rule_based_analyze(transcription, duration)

        chapters = []
        for item in parsed:
            try:
                chapters.append(Chapter(
                    id=str(uuid4()),
                    title=item.get("title", "Untitled Chapter"),
                    start=float(item.get("start", 0)),
                    end=float(item.get("end", 0)),
                    duration=float(item.get("end", 0)) - float(item.get("start", 0)),
                    summary=item.get("summary"),
                    confidence=float(item.get("confidence", 0.8)),
                    hooks=item.get("hooks", []),
                ))
            except (ValueError, KeyError):
                continue

        return chapters if chapters else self._rule_based_analyze(transcription, duration)

    def _rule_based_analyze(
        self,
        transcription: str,
        duration: float,
        min_duration: float = 30,
        max_duration: float = 90,
    ) -> list[Chapter]:
        """
        Rule-based chapter extraction.

        Splits transcription into coherent segments based on:
        - Sentence boundaries
        - Topic changes (detected by keyword patterns)
        - Duration constraints
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', transcription.strip())

        if not sentences:
            return []

        chapters = []
        current_chapter = []
        current_start = 0.0

        # Estimate timing (uniform distribution as fallback)
        time_per_char = duration / len(transcription) if transcription else 0.1

        for sentence in sentences:
            if not sentence.strip():
                continue

            current_chapter.append(sentence)

            # Estimate current duration
            current_text = " ".join(current_chapter)
            estimated_duration = len(current_text) * time_per_char

            # Check if we should end the chapter
            if min_duration <= estimated_duration <= max_duration:
                chapters.append(Chapter(
                    id=str(uuid4()),
                    title=self._generate_title(current_text),
                    start=current_start,
                    end=min(current_start + estimated_duration, duration),
                    duration=estimated_duration,
                    summary=current_text[:200] + "..." if len(current_text) > 200 else current_text,
                    confidence=0.6,
                    hooks=self._extract_hooks(current_text),
                ))
                current_chapter = []
                current_start += estimated_duration
            elif estimated_duration > max_duration:
                # Force split
                chapters.append(Chapter(
                    id=str(uuid4()),
                    title=self._generate_title(current_text),
                    start=current_start,
                    end=min(current_start + max_duration, duration),
                    duration=max_duration,
                    summary=current_text[:200] + "..." if len(current_text) > 200 else current_text,
                    confidence=0.5,
                    hooks=self._extract_hooks(current_text),
                ))
                current_chapter = []
                current_start += max_duration

        # Handle remaining text
        if current_chapter and current_start < duration:
            remaining_text = " ".join(current_chapter)
            remaining_duration = duration - current_start
            if remaining_duration >= 15:  # Only add if substantial
                chapters.append(Chapter(
                    id=str(uuid4()),
                    title=self._generate_title(remaining_text),
                    start=current_start,
                    end=duration,
                    duration=remaining_duration,
                    summary=remaining_text[:200] + "..." if len(remaining_text) > 200 else remaining_text,
                    confidence=0.5,
                    hooks=self._extract_hooks(remaining_text),
                ))

        return chapters

    def _generate_title(self, text: str) -> str:
        """Generate a title from text."""
        # Get first few meaningful words
        words = text.strip().split()[:6]
        title = " ".join(words)

        # Remove trailing punctuation
        title = re.sub(r'[.!?,:;]+$', '', title)

        # Capitalize
        return title.capitalize() if title else "Untitled Segment"

    def _extract_hooks(self, text: str) -> list[str]:
        """Extract potential viral hooks from text."""
        hooks = []

        # Look for questions
        questions = re.findall(r'\?[^.]*', text)
        hooks.extend(questions[:2])

        # Look for exclamatory statements
        exclamations = re.findall(r'[A-Z][^.!?]*[!?]', text)
        hooks.extend(exclamations[:2])

        # Look for "You won't believe" type phrases
        patterns = [
            r'(You (won\'t|will not) believe|This is )[^.!?]*[.!?]',
            r'(The secret|The truth) (of|about|is)[^.!?]*[.!?]',
            r'(Wait|Stop|Hold on)[^.!?]*[.!?]',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            hooks.extend([m[0] if isinstance(m, tuple) else m for m in matches[:1]])

        return [h.strip() for h in hooks[:3] if len(h.strip()) > 10]

    def generate_hook(
        self,
        chapter: Chapter,
        context: str = "",
    ) -> Optional[str]:
        """
        Generate a viral hook for a chapter using AI.

        Args:
            chapter: Chapter to generate hook for
            context: Additional context from video

        Returns:
            Generated hook text or None
        """
        if not self.ai_client or not self.ai_client.is_configured():
            return chapter.hooks[0] if chapter.hooks else None

        prompt = self.ai_client.format_hook_prompt(
            {"title": chapter.title, "summary": chapter.summary},
            context or chapter.summary or "",
        )

        response = self.ai_client.generate(prompt, json_mode=True)

        if not self.ai_client.validate_response(response):
            return None

        parsed = self.ai_client.parse_json_response(response.content)
        if parsed and isinstance(parsed, list):
            return parsed[0] if parsed else None

        return None

    def score_viral_potential(
        self,
        chapter: Chapter,
        transcription: str = "",
    ) -> int:
        """
        Score a chapter's viral potential (0-100).

        Args:
            chapter: Chapter to score
            transcription: Full transcription for context

        Returns:
            Viral score 0-100
        """
        score = 50  # Base score

        # Length factor (30-60s is optimal)
        if 30 <= chapter.duration <= 60:
            score += 20
        elif 60 < chapter.duration <= 90:
            score += 10
        elif chapter.duration < 20:
            score -= 20

        # Hooks factor
        if chapter.hooks:
            score += min(len(chapter.hooks) * 5, 15)

        # Question in summary
        if chapter.summary and "?" in chapter.summary:
            score += 5

        # Title length (shorter is punchier)
        if len(chapter.title.split()) <= 5:
            score += 5

        # Confidence factor
        score += int(chapter.confidence * 20)

        # Keywords that suggest viral content
        viral_keywords = [
            "secret", "hack", "trick", "amazing", "unbelievable",
            "shocking", "incredible", "must see", "you won't",
            "finally", "discover", "learn", "how to",
        ]
        text = (chapter.title + " " + (chapter.summary or "")).lower()
        for keyword in viral_keywords:
            if keyword in text:
                score += 2

        return min(max(score, 0), 100)
