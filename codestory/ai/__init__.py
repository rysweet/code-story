from __future__ import annotations
from typing import Any, List

from pydantic import BaseModel, Field, ValidationError
from codestory.config import Settings, get_settings  # type: ignore

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

    async def chat(self, messages: list[dict[str, Any]]) -> str:  # noqa: D401
        raise NotImplementedError("Chat completions not implemented yet.")

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError("Embedding not implemented yet.")

__all__ = ["AIClient"]