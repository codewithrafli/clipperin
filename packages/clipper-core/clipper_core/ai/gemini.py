"""Google Gemini AI client."""

import os
from typing import Optional

from clipper_core.ai.base import AIClient, AIResponse, AIMessage


class GeminiClient(AIClient):
    """
    Google Gemini AI client.

    Uses the generativeai SDK for content analysis.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key, model)
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize the Gemini client."""
        try:
            import google.generativeai as genai

            api_key = self.api_key or os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self._client = genai.GenerativeModel(self.get_model())
        except ImportError:
            self._client = None

    def is_configured(self) -> bool:
        """Check if Gemini is properly configured."""
        return bool(self._client) and bool(self.api_key or os.getenv("GEMINI_API_KEY"))

    def get_default_model(self) -> str:
        """Get the default Gemini model."""
        return "gemini-1.5-flash"

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate a response from Gemini."""
        if not self.is_configured():
            return AIResponse(content="", model=self.get_model())

        try:
            response = self._client.generate_content(
                prompt,
                generation_config=kwargs.get("generation_config"),
            )
            content = response.text if response.text else ""
            tokens = response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0

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
        """Generate a chat response from Gemini."""
        if not self.is_configured():
            return AIResponse(content="", model=self.get_model())

        try:
            # Convert messages to Gemini format
            history = []
            for msg in messages[:-1]:
                role = "user" if msg.role == "user" else "model"
                history.append({"role": role, "parts": [msg.content]})

            chat = self._client.start_chat(history=history)
            response = chat.send_message(messages[-1].content)

            content = response.text if response.text else ""
            tokens = response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0

            return AIResponse(
                content=content,
                model=self.get_model(),
                tokens_used=tokens,
                cost_estimate=self.estimate_cost(self.get_model(), tokens),
                raw=response,
            )
        except Exception as e:
            return AIResponse(content="", model=self.get_model(), raw=str(e))
