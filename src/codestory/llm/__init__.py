"""Azure OpenAI client for Code Story.

This module provides a client for accessing Azure OpenAI services,
including both synchronous and asynchronous APIs for completions,
chat, and embeddings.
"""

from .client import OpenAIClient, create_client
from .exceptions import (
    OpenAIError,
    AuthenticationError,
    RateLimitError,
    InvalidRequestError,
    ServiceUnavailableError,
    TimeoutError,
    ContextLengthError,
)
from .models import (
    CompletionRequest,
    CompletionResponse,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ChatMessage,
    ChatRole,
)

__all__ = [
    # Client
    "OpenAIClient",
    "create_client",
    
    # Exceptions
    "OpenAIError",
    "AuthenticationError",
    "RateLimitError",
    "InvalidRequestError",
    "ServiceUnavailableError",
    "TimeoutError",
    "ContextLengthError",
    
    # Models
    "CompletionRequest",
    "CompletionResponse",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "ChatMessage",
    "ChatRole",
]