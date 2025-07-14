from __future__ import annotations

from pydantic import ValidationError
from codestory.config import get_settings  # type: ignore


class AIClient:
    """
    Async Azure OpenAI client wrapper with minimal stubbed methods.
    """

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or getattr(settings, "openai_api_key", None)
        if not self.api_key:
            raise ValidationError(
                [
                    {
                        "loc": ("api_key",),
                        "msg": "API key missing",
                        "type": "value_error.missing",
                    }
                ],
                model=AIClient,
            )

    async def chat(self, prompt: str) -> str:
        return f"Echo: {prompt}"

    async def embed(self, text: str) -> list[float]:
        return [0.0]


__all__ = ["AIClient"]
