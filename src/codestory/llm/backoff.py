"""Retry and backoff logic for OpenAI API calls.

This module provides retry logic with exponential backoff for handling
rate limiting and transient errors from the Azure OpenAI API.
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar, cast

import openai
from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import (
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
)
from .metrics import OperationType, record_retry

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])

# Set up logging
logger = logging.getLogger(__name__)


def get_retry_after(retry_state: RetryCallState) -> float | None:
    """Get retry-after time from the exception.

    Args:
        retry_state: Current retry state

    Returns:
        Time to wait before retrying in seconds, or None if no retry_after is specified
    """
    exception = retry_state.outcome.exception()
    if exception is not None and hasattr(exception, "retry_after") and exception.retry_after is not None:
        return float(min(exception.retry_after, 60))  # Cap at 60 seconds

    # Return None when no retry_after is specified to allow exponential backoff to handle timing
    return None


def before_retry_callback(retry_state: RetryCallState) -> None:
    """Log and collect metrics before a retry.

    Args:
        retry_state: Current retry state
    """
    exception = retry_state.outcome.exception()
    attempt = retry_state.attempt_number

    operation = getattr(retry_state.kwargs.get("_operation_type", None), "value", "unknown")
    model = retry_state.kwargs.get("model", "unknown")

    wait_time = retry_state.next_action.sleep

    logger.warning(
        f"Retrying {operation} request to model {model} after error: {exception!s}. "
        f"Attempt {attempt}, waiting {wait_time:.2f} seconds..."
    )

    # Record retry in metrics
    operation_type = retry_state.kwargs.get("_operation_type")
    if operation_type:
        record_retry(operation_type, model)


def retry_on_openai_errors(
    max_retries: int = 5,
    retry_backoff_factor: float = 2.0,
    operation_type: OperationType | None = None,
) -> Callable[[F], F]:
    """Decorator for retrying OpenAI API calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        retry_backoff_factor: Multiplier for exponential backoff
        operation_type: Type of operation for metrics collection

    Returns:
        Decorator function that implements retry logic
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=retry_backoff_factor, min=1, max=60),
            retry=retry_if_exception_type(
                (
                    RateLimitError,
                    ServiceUnavailableError,
                    TimeoutError,
                    openai.RateLimitError,
                    openai.APIConnectionError,
                    openai.APITimeoutError,
                )
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=before_retry_callback,
        )
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Inject operation type into kwargs for metric collection
            if operation_type:
                kwargs["_operation_type"] = operation_type

            try:
                return func(*args, **kwargs)
            except openai.RateLimitError as e:
                # Get retry-after time from headers if available
                retry_after = None
                if hasattr(e, "headers") and e.headers:
                    retry_after = e.headers.get("retry-after")
                    if retry_after:
                        try:
                            retry_after = int(retry_after)
                        except (ValueError, TypeError):
                            retry_after = None

                raise RateLimitError(
                    f"Rate limit exceeded: {e!s}", retry_after=retry_after, cause=e
                ) from e
            except openai.APIConnectionError as e:
                raise ServiceUnavailableError(f"API connection error: {e!s}", cause=e) from e
            except openai.APITimeoutError as e:
                raise TimeoutError(f"API request timed out: {e!s}", cause=e) from e
            except openai.BadRequestError as e:
                # Check for context length error
                if "maximum context length" in str(e).lower():
                    from .exceptions import ContextLengthError

                    raise ContextLengthError(
                        f"Input context length exceeded model maximum: {e!s}",
                        cause=e,
                    ) from e

                from .exceptions import InvalidRequestError

                raise InvalidRequestError(f"Invalid request: {e!s}", cause=e) from e
            except openai.AuthenticationError as e:
                from .exceptions import AuthenticationError

                raise AuthenticationError(f"Authentication error: {e!s}", cause=e) from e
            except openai.APIError as e:
                raise ServiceUnavailableError(f"API error: {e!s}", cause=e) from e
            except Exception as e:
                # Re-raise other exceptions
                raise e

        return cast("F", wrapper)

    return decorator


def retry_on_openai_errors_async(
    max_retries: int = 5,
    retry_backoff_factor: float = 2.0,
    operation_type: OperationType | None = None,
) -> Callable[[F], F]:
    """Decorator for retrying async OpenAI API calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        retry_backoff_factor: Multiplier for exponential backoff
        operation_type: Type of operation for metrics collection

    Returns:
        Decorator function that implements retry logic for async functions
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=retry_backoff_factor, min=1, max=60),
            retry=retry_if_exception_type(
                (
                    RateLimitError,
                    ServiceUnavailableError,
                    TimeoutError,
                    openai.RateLimitError,
                    openai.APIConnectionError,
                    openai.APITimeoutError,
                )
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=before_retry_callback,
        )
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Inject operation type into kwargs for metric collection
            if operation_type:
                kwargs["_operation_type"] = operation_type

            try:
                return await func(*args, **kwargs)
            except openai.RateLimitError as e:
                # Get retry-after time from headers if available
                retry_after = None
                if hasattr(e, "headers") and e.headers:
                    retry_after = e.headers.get("retry-after")
                    if retry_after:
                        try:
                            retry_after = int(retry_after)
                        except (ValueError, TypeError):
                            retry_after = None

                raise RateLimitError(
                    f"Rate limit exceeded: {e!s}", retry_after=retry_after, cause=e
                ) from e
            except openai.APIConnectionError as e:
                raise ServiceUnavailableError(f"API connection error: {e!s}", cause=e) from e
            except openai.APITimeoutError as e:
                raise TimeoutError(f"API request timed out: {e!s}", cause=e) from e
            except openai.BadRequestError as e:
                # Check for context length error
                if "maximum context length" in str(e).lower():
                    from .exceptions import ContextLengthError

                    raise ContextLengthError(
                        f"Input context length exceeded model maximum: {e!s}",
                        cause=e,
                    ) from e

                from .exceptions import InvalidRequestError

                raise InvalidRequestError(f"Invalid request: {e!s}", cause=e) from e
            except openai.AuthenticationError as e:
                from .exceptions import AuthenticationError

                raise AuthenticationError(f"Authentication error: {e!s}", cause=e) from e
            except openai.APIError as e:
                raise ServiceUnavailableError(f"API error: {e!s}", cause=e) from e
            except Exception as e:
                # Re-raise other exceptions
                raise e

        return cast("F", wrapper)

    return decorator