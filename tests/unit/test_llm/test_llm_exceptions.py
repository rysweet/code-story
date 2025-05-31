"""Tests for OpenAI client exceptions."""

from codestory.llm.exceptions import (
    AuthenticationError,
    ContextLengthError,
    InvalidRequestError,
    OpenAIError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
)


def test_llm_openai_error_base() -> None:
    """Test OpenAIError instantiation."""
    # Test basic error
    error = OpenAIError("Test message")
    assert str(error) == "Test message"
    assert error.message == "Test message"
    assert error.details == {}
    assert error.cause is None

    # Test with details
    details = {"model": "gpt-4", "tokens": 1000}
    error = OpenAIError("Test message", details=details)
    assert error.message == "Test message"
    assert error.details == details

    # Test with cause
    cause = ValueError("Original error")
    error = OpenAIError("Test message", cause=cause)
    assert error.cause == cause
    assert "caused by: Original error" in str(error)


def test_llm_authentication_error() -> None:
    """Test AuthenticationError."""
    error = AuthenticationError("Invalid API key")
    assert isinstance(error, OpenAIError)
    assert str(error) == "Invalid API key"


def test_llm_rate_limit_error() -> None:
    """Test RateLimitError."""
    # Basic rate limit error
    error = RateLimitError("Rate limit exceeded")
    assert isinstance(error, OpenAIError)
    assert error.retry_after is None

    # With retry_after
    error = RateLimitError("Rate limit exceeded", retry_after=30)
    assert error.retry_after == 30


def test_llm_invalid_request_error() -> None:
    """Test InvalidRequestError."""
    error = InvalidRequestError("Invalid model name")
    assert isinstance(error, OpenAIError)
    assert str(error) == "Invalid model name"


def test_llm_service_unavailable_error() -> None:
    """Test ServiceUnavailableError."""
    error = ServiceUnavailableError("Service is currently unavailable")
    assert isinstance(error, OpenAIError)
    assert str(error) == "Service is currently unavailable"


def test_llm_timeout_error() -> None:
    """Test TimeoutError."""
    error = TimeoutError("Request timed out after 60s")
    assert isinstance(error, OpenAIError)
    assert str(error) == "Request timed out after 60s"


def test_llm_context_length_error() -> None:
    """Test ContextLengthError."""
    # Basic error
    error = ContextLengthError("Context length exceeded")
    assert isinstance(error, InvalidRequestError)
    assert error.max_tokens is None
    assert error.input_tokens is None

    # With token counts
    error = ContextLengthError("Context length exceeded", max_tokens=8192, input_tokens=9000)
    assert error.max_tokens == 8192
    assert error.input_tokens == 9000
