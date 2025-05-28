"""Azure OpenAI client for Code Story.

This module provides a client for accessing Azure OpenAI services,
including both synchronous and asynchronous APIs for completions,
chat, and embeddings.
"""

from .client import OpenAIClient, create_client
from .exceptions import (
    AuthenticationError,
    ContextLengthError,
    InvalidRequestError,
    OpenAIError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
)
from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ChatRole,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)

__all__ = [
    "AuthenticationError",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
    "ChatRole",
    # Models
    "CompletionRequest",
    "CompletionResponse",
    "ContextLengthError",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "InvalidRequestError",
    # Client
    "OpenAIClient",
    # Exceptions
    "OpenAIError",
    "RateLimitError",
    "ServiceUnavailableError",
    "TimeoutError",
    "create_client",
]
