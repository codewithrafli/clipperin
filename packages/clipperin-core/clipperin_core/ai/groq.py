"""Groq AI client."""

import os
from typing import Optional

from clipperin_core.ai.base import AIClient, AIResponse, AIMessage


class GroqClient(AIClient):
    """
    Groq AI client.

    Uses the OpenAI-compatible API for fast inference.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key, model)
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize the Groq client."""
        try:
            from groq import Groq

            api_key = self.api_key or os.getenv("GROQ_API_KEY")
            if api_key:
                self._client = Groq(api_key=api_key)
        except ImportError:
            self._client = None

    def is_configured(self) -> bool:
        """Check if Groq is properly configured."""
        return bool(self._client) and bool(self.api_key or os.getenv("GROQ_API_KEY"))

    def get_default_model(self) -> str:
        """Get the default Groq model."""
        return "llama-3.3-70b-versatile"

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate a response from Groq."""
        if not self.is_configured():
            return AIResponse(content="", model=self.get_model())

        try:
            response = self._client.chat.completions.create(
                model=self.get_model(),
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
                response_format={"type": "json_object"} if kwargs.get("json_mode") else None,
            )

            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens

            return AIResponse(
                content=content,
                model=self.get_model(),
                tokens_used=tokens,
                cost_estimate=self.estimate_cost(self.get_model(), tokens),
                raw=response,
            )
        except Exception as e:
            return AIResponse(content="", model=self.get_model(), raw=str(e))

    def chat(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        """Generate a chat response from Groq."""
        if not self.is_configured():
            return AIResponse(content="", model=self.get_model())

        try:
            formatted = [{"role": m.role, "content": m.content} for m in messages]
            response = self._client.chat.completions.create(
                model=self.get_model(),
                messages=formatted,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
                response_format={"type": "json_object"} if kwargs.get("json_mode") else None,
            )

            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens

            return AIResponse(
                content=content,
                model=self.get_model(),
                tokens_used=tokens,
                cost_estimate=self.estimate_cost(self.get_model(), tokens),
                raw=response,
            )
        except Exception as e:
            return AIResponse(content="", model=self.get_model(), raw=str(e))
