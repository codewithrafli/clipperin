"""Base AI client and common types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIMessage:
    """A message in an AI conversation."""

    role: str  # system, user, assistant
    content: str


@dataclass
class AIResponse:
    """Response from an AI provider."""

    content: str
    model: str
    tokens_used: int = 0
    cost_estimate: float = 0.0  # In USD
    raw: Any = None  # Raw response for debugging

    def __str__(self) -> str:
        return self.content


class AIClient(ABC):
    """
    Abstract base class for AI clients.

    All AI providers must implement this interface.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.model = model
        self._client = None

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate a response from the AI."""
        pass

    @abstractmethod
    def chat(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        """Generate a response from a chat conversation."""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        pass

    def get_model(self) -> str:
        """Get the configured model or default."""
        return self.model or self.get_default_model()

    def estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost in USD for a given model and token count."""
        # Rough estimates as of 2024
        costs = {
            "gemini": 0.000001,  # $1 per million
            "llama": 0.0000001,  # Groq is very cheap
            "gpt-4o-mini": 0.00015,  # $0.15 per million
            "gpt-4o": 0.0025,
        }
        for key, cost in costs.items():
            if key in model.lower():
                return cost * tokens
        return 0.0

    def validate_response(self, response: AIResponse) -> bool:
        """Validate that the response is usable."""
        return bool(response.content and response.content.strip())

    def format_chapters_prompt(self, transcription: str, video_info: dict = None) -> str:
        """Format a prompt for chapter analysis."""
        return f"""Analyze this video transcription and extract the most engaging segments.

Transcription:
{transcription}

Return a JSON array of chapters with this structure:
[
  {{
    "title": "Engaging title",
    "start": 0.0,
    "end": 45.0,
    "summary": "Brief summary",
    "confidence": 0.85,
    "hooks": ["Hook 1", "Hook 2"]
  }}
]

Guidelines:
- Each chapter should be 30-90 seconds long
- Focus on self-contained, interesting segments
- Include viral-worthy hooks if possible
- Start/end at natural sentence boundaries
- Include timestamps in seconds
"""

    def format_hook_prompt(self, chapter: dict, context: str = "") -> str:
        """Format a prompt for generating a viral hook."""
        return f"""Generate a viral hook text for this video segment.

Title: {chapter.get('title', 'Clip')}
Content: {context}

Generate 1-3 short, punchy hook options (max 5 words each) that would:
- Grab attention in the first second
- Create curiosity
- Be perfect for TikTok/Reels

Return as a JSON array of strings:
["Hook 1", "Hook 2", "Hook 3"]
"""

    def parse_json_response(self, response: str) -> Any:
        """Safely parse JSON from AI response."""
        import json
        import re

        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            # Try to find any JSON-like structure
            match = re.search(r"\{.*\}|\[.*\]", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return None
