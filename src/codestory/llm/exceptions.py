"""Exceptions for the OpenAI client.

This module defines custom exception types for various error conditions
that can occur when interacting with the Azure OpenAI API.
"""

from typing import Any, Dict, Optional


class OpenAIError(Exception):
    """Base exception for all OpenAI-related errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize OpenAIError.

        Args:
            message: Human-readable error message
            details: Additional error details
            cause: Original exception that caused this error
        """
        self.message = message
        self.details = details or {}
        self.cause = cause

        if cause:
            super().__init__(f"{message} - caused by: {str(cause)}")
        else:
            super().__init__(message)


class AuthenticationError(OpenAIError):
    """Error with API key or authentication."""

    pass


class RateLimitError(OpenAIError):
    """Rate limit or quota exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs,
    ) -> None:
        """Initialize RateLimitError.

        Args:
            message: Human-readable error message
            retry_after: Suggested wait time in seconds
            **kwargs: Additional arguments to pass to the base class
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class InvalidRequestError(OpenAIError):
    """Invalid request parameters."""

    pass


class ServiceUnavailableError(OpenAIError):
    """OpenAI service unavailable or internal server error."""

    pass


class TimeoutError(OpenAIError):
    """Request timed out."""

    pass


class ContextLengthError(InvalidRequestError):
    """Input context length exceeded maximum for model."""

    def __init__(
        self,
        message: str,
        max_tokens: Optional[int] = None,
        input_tokens: Optional[int] = None,
        **kwargs,
    ) -> None:
        """Initialize ContextLengthError.

        Args:
            message: Human-readable error message
            max_tokens: Maximum tokens allowed for the model
            input_tokens: Number of tokens in the input
            **kwargs: Additional arguments to pass to the base class
        """
        super().__init__(message, **kwargs)
        self.max_tokens = max_tokens
        self.input_tokens = input_tokens
