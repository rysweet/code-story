"""Data models for OpenAI API requests and responses.

This module defines Pydantic models for serializing and deserializing
requests and responses for the Azure OpenAI API.
"""

import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRole(str, Enum):
    """Roles for chat messages."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A message in a chat conversation."""

    role: ChatRole
    content: str
    name: str | None = None

    model_config = ConfigDict(extra="allow")


class ChatFunctionCall(BaseModel):
    """A function call in a chat response."""

    name: str
    arguments: str

    model_config = ConfigDict(extra="allow")


class ChatResponseMessage(BaseModel):
    """A message in a chat completion response."""

    role: ChatRole
    content: str | None = None
    function_call: ChatFunctionCall | None = None
    tool_calls: list[dict[str, Any]] | None = None

    model_config = ConfigDict(extra="allow")


class ChatResponseChoice(BaseModel):
    """A choice in a chat completion response."""

    index: int
    message: ChatResponseMessage
    finish_reason: str | None = None

    model_config = ConfigDict(extra="allow")


# Aliases for backward compatibility
ChatCompletionResponseChoice = ChatResponseChoice


class CompletionChoice(BaseModel):
    """A choice in a completion response."""

    text: str
    index: int
    finish_reason: str | None = None
    logprobs: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class EmbeddingData(BaseModel):
    """Embedding data for a single input."""

    embedding: list[float]
    index: int
    object: str = "embedding"

    model_config = ConfigDict(extra="allow")


class UsageInfo(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int | None = None
    total_tokens: int

    model_config = ConfigDict(extra="allow")


# Aliases for backward compatibility
Usage = UsageInfo


# Request Models


class CompletionRequest(BaseModel):
    """Parameters for a completion request."""

    model: str
    prompt: str | list[str] | list[int] | list[list[int]]
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    n: int | None = None
    stream: bool | None = None
    logprobs: int | None = None
    stop: str | list[str] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    best_of: int | None = None
    user: str | None = None

    model_config = ConfigDict(extra="allow")


class ChatCompletionRequest(BaseModel):
    """Parameters for a chat completion request."""

    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    n: int | None = None
    stream: bool | None = None
    stop: str | list[str] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    logit_bias: dict[str, float] | None = None
    user: str | None = None
    functions: list[dict[str, Any]] | None = None
    function_call: str | dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    response_format: dict[str, str] | None = None

    model_config = ConfigDict(extra="allow")


class EmbeddingRequest(BaseModel):
    """Parameters for an embedding request."""

    model: str
    input: str | list[str] | list[int] | list[list[int]]
    user: str | None = None
    dimensions: int | None = None

    model_config = ConfigDict(extra="allow")


# Response Models


class CompletionResponse(BaseModel):
    """Response from a completion request."""

    id: str
    object: str
    created: int
    model: str
    choices: list[CompletionChoice]
    usage: UsageInfo | None = None

    model_config = ConfigDict(extra="allow")


class ChatCompletionResponse(BaseModel):
    """Response from a chat completion request."""

    id: str
    object: str
    created: int
    model: str
    choices: list[ChatResponseChoice]
    usage: UsageInfo | None = None

    model_config = ConfigDict(extra="allow")


class EmbeddingResponse(BaseModel):
    """Response from an embedding request."""

    object: str
    data: list[EmbeddingData]
    model: str
    usage: UsageInfo

    model_config = ConfigDict(extra="allow")


# Extended models for resilient LLM operation


class LLMProvider(str, Enum):
    """LLM provider type."""

    OPENAI = "openai"  # OpenAI direct API
    AZURE_OPENAI = "azure_openai"  # Azure-hosted OpenAI
    MOCK = "mock"  # Mock provider for testing


class LLMMode(str, Enum):
    """LLM operating mode."""

    NORMAL = "normal"  # Normal operation mode using Azure credentials
    FALLBACK = "fallback"  # Fallback mode using direct API key
    MOCK = "mock"  # Mock mode for testing without real API calls
    DISABLED = "disabled"  # Disabled mode (no LLM calls allowed)


class LLMConfiguration(BaseModel):
    """Configuration for resilient LLM operations."""

    # Primary configuration
    mode: LLMMode = Field(default=LLMMode.NORMAL, description="Current LLM operation mode")
    provider: LLMProvider = Field(default=LLMProvider.OPENAI, description="LLM provider")

    # Fallback configuration
    allow_fallback: bool = Field(
        default=True,
        description="Whether to allow automatic fallback to API key auth when Azure auth fails",
    )
    fallback_api_key: str | None = Field(
        default=None, description="Fallback API key to use when Azure auth fails"
    )

    # Environment variables for configuration
    @classmethod
    def from_environment(cls) -> "LLMConfiguration":
        """Create an LLMConfiguration instance from environment variables."""
        # Check environment variables for mode setting
        mode_str = os.environ.get("CODESTORY_LLM_MODE", "normal").lower()
        provider_str = os.environ.get("CODESTORY_LLM_PROVIDER", "openai").lower()

        # Parse mode with validation
        try:
            mode = LLMMode(mode_str)
        except ValueError:
            mode = LLMMode.NORMAL

        # Parse provider with validation
        try:
            provider = LLMProvider(provider_str)
        except ValueError:
            provider = LLMProvider.OPENAI

        # Check for fallback configuration
        allow_fallback = os.environ.get("CODESTORY_LLM_ALLOW_FALLBACK", "true").lower() in [
            "true",
            "1",
            "yes",
        ]
        fallback_api_key = os.environ.get("OPENAI__API_KEY", None)

        # Note: CODESTORY_NO_MODEL_CHECK is no longer used
        # We always require a working OpenAI model

        return cls(
            mode=mode,
            provider=provider,
            allow_fallback=allow_fallback,
            fallback_api_key=fallback_api_key,
        )
