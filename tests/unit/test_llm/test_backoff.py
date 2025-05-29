"""Tests for OpenAI client retry and backoff logic."""

from unittest.mock import MagicMock, patch

import openai
import pytest

from codestory.llm.backoff import (
    before_retry_callback,
    get_retry_after,
    retry_on_openai_errors,
    retry_on_openai_errors_async,
)
from codestory.llm.exceptions import (
    ContextLengthError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
)
from codestory.llm.metrics import OperationType


# Create mock fixture to prevent real Prometheus metrics from being used
@pytest.fixture(autouse=True)
def mock_all_prometheus() -> None:
    """Mock all Prometheus metrics objects before any module imports."""
    with (
        patch("prometheus_client.Counter") as mock_counter,
        patch("prometheus_client.Gauge") as mock_gauge,
        patch("prometheus_client.Histogram") as mock_histogram,
        patch("prometheus_client.registry.REGISTRY._names_to_collectors", {}),
        patch("codestory.llm.metrics.record_retry"),
    ):
        # Configure the mocks to behave like the real counters
        mock_labels = MagicMock()
        mock_counter.return_value.labels = mock_labels
        mock_gauge.return_value.labels = mock_labels
        mock_histogram.return_value.labels = mock_labels

        yield


class TestRetryFunctions:
    """Tests for retry utility functions."""

    def test_get_retry_after(self) -> None:
        """Test get_retry_after function."""
        # Create a mock retry state with an exception that has retry_after
        retry_state = MagicMock()
        exception = RateLimitError("Rate limit exceeded", retry_after=30)
        retry_state.outcome.exception.return_value = exception

        # Test with retry_after provided
        result = get_retry_after(retry_state)
        assert result == 30

        # Test with large retry_after value (should cap at 60)
        exception = RateLimitError("Rate limit exceeded", retry_after=120)
        retry_state.outcome.exception.return_value = exception
        result = get_retry_after(retry_state)
        assert result == 60

        # Test with no retry_after
        exception = RateLimitError("Rate limit exceeded")
        retry_state.outcome.exception.return_value = exception
        result = get_retry_after(retry_state)
        assert result is None

    def test_before_retry_callback(self) -> None:
        """Test before_retry_callback function."""
        # Create a mock retry state
        retry_state = MagicMock()
        retry_state.attempt_number = 2
        retry_state.kwargs = {"_operation_type": OperationType.CHAT, "model": "gpt-4o"}
        retry_state.next_action.sleep = 4.0
        exception = RateLimitError("Rate limit exceeded")
        retry_state.outcome.exception.return_value = exception

        # Test with operation type
        with patch("codestory.llm.backoff.record_retry") as mock_record:
            before_retry_callback(retry_state)
            mock_record.assert_called_once_with(OperationType.CHAT, "gpt-4o")

        # Test without operation type
        retry_state.kwargs = {"model": "gpt-4o"}
        with patch("codestory.llm.backoff.record_retry") as mock_record:
            before_retry_callback(retry_state)
            mock_record.assert_not_called()


class TestRetryDecorators:
    """Tests for retry decorators."""

    def test_retry_on_openai_errors(self) -> None:
        """Test the retry_on_openai_errors decorator."""
        # Create a test function that raises different types of errors
        mock_func = MagicMock()

        # Set up successive side effects: first fails, second fails, third succeeds
        mock_func.side_effect = [
            RateLimitError("Rate limit exceeded"),
            ServiceUnavailableError("Service unavailable"),
            "Success Result",  # This will be returned on the third call
        ]

        # Apply the decorator
        # Need to patch retry to control its behavior for testing
        with patch("codestory.llm.backoff.retry") as mock_retry:
            # Make the mock retry actually execute the function directly without retrying
            mock_retry.return_value = lambda f: f

            # Apply our decorator
            decorator = retry_on_openai_errors(max_retries=3, operation_type=OperationType.CHAT)
            decorated_func = decorator(mock_func)

            # First call should raise RateLimitError
            try:
                decorated_func(model="gpt-4o")
                pytest.fail("Expected RateLimitError")
            except RateLimitError:
                pass

            # Second call should raise ServiceUnavailableError
            try:
                decorated_func(model="gpt-4o")
                pytest.fail("Expected ServiceUnavailableError")
            except ServiceUnavailableError:
                pass

            # Third call should succeed
            result = decorated_func(model="gpt-4o")
            assert result == "Success Result"

            # Verify the operation type was injected
            assert "_operation_type" in mock_func.call_args[1]
            assert mock_func.call_args[1]["_operation_type"] == OperationType.CHAT

    def test_exception_conversion_rate_limit(self) -> None:
        """Test conversion of RateLimitError."""
        with patch("codestory.llm.backoff.retry") as mock_retry:
            mock_retry.return_value = lambda f: f

            # Define a function that raises OpenAI RateLimitError
            def test_func() -> None:
                raise openai.RateLimitError(
                    message="Rate limit exceeded", response=MagicMock(), body=None
                )

            # Apply our decorator
            decorated_func = retry_on_openai_errors(max_retries=1)(test_func)

            # Call the decorated function and expect our custom exception
            with pytest.raises(RateLimitError):
                decorated_func()

    def test_exception_conversion_api_connection(self) -> None:
        """Test conversion of APIConnectionError."""
        with patch("codestory.llm.backoff.retry") as mock_retry:
            mock_retry.return_value = lambda f: f

            # Define a function that raises OpenAI APIConnectionError
            def test_func() -> None:
                raise openai.APIConnectionError(message="Connection error", request=MagicMock())

            # Apply our decorator
            decorated_func = retry_on_openai_errors(max_retries=1)(test_func)

            # Call the decorated function and expect our custom exception
            with pytest.raises(ServiceUnavailableError):
                decorated_func()

    def test_exception_conversion_timeout(self) -> None:
        """Test TimeoutError conversion directly."""
        with patch("codestory.llm.backoff.retry") as mock_retry:
            mock_retry.return_value = lambda f: f

            # Create a simpler test function that mimics APITimeoutError behavior
            # Just inspect how APITimeoutError is created in the actual code
            class MockAPITimeoutError(Exception):
                def __init__(self) -> None:
                    self.message = "Request timed out"
                    super().__init__(self.message)

            # Define a function that raises our mock timeout error
            def test_func() -> None:
                # Instead of trying to create a complex object,
                # we patch the place where openai.APITimeoutError is used
                with patch("openai.APITimeoutError", MockAPITimeoutError):
                    raise MockAPITimeoutError()

            # Apply our decorator with patched behavior
            with patch("openai.APITimeoutError", MockAPITimeoutError):
                decorated_func = retry_on_openai_errors(max_retries=1)(test_func)

                # Call the decorated function and expect our custom TimeoutError
                with pytest.raises(TimeoutError) as exc_info:
                    decorated_func()

                # Verify the exception has the correct message
                assert "API request timed out" in str(exc_info.value)
                # Our mock won't be the actual cause due to the patching
                # but we can check that the exception contains the right message
                assert "Request timed out" in str(exc_info.value)

    def test_exception_conversion_context_length(self) -> None:
        """Test conversion of BadRequestError for context length."""
        with patch("codestory.llm.backoff.retry") as mock_retry:
            mock_retry.return_value = lambda f: f

            # Define a function that raises OpenAI BadRequestError for context length
            def test_func() -> None:
                raise openai.BadRequestError(
                    message="Input context length exceeded maximum context length",
                    response=MagicMock(),
                    body=None,
                )

            # Apply our decorator
            decorated_func = retry_on_openai_errors(max_retries=1)(test_func)

            # Call the decorated function and expect our custom exception
            with pytest.raises(ContextLengthError):
                decorated_func()

    def test_retry_on_openai_errors_retry_after(self) -> None:
        """Test that retry_after is extracted from headers."""
        with patch("codestory.llm.backoff.retry") as mock_retry:
            # Make the mock retry actually execute the function directly
            mock_retry.return_value = lambda f: f

            # Create a function that raises a rate limit error with headers
            def test_retry_after() -> None:
                e = openai.RateLimitError(
                    message="Rate limit exceeded", response=MagicMock(), body=None
                )
                e.headers = {"retry-after": "30"}
                raise e

            # Apply our decorator
            decorated_func = retry_on_openai_errors(max_retries=1)(test_retry_after)

            # The test should capture the converted exception
            with pytest.raises(RateLimitError) as exc_info:
                decorated_func()

            # Check that retry_after was extracted
            assert exc_info.value.retry_after == 30

    def test_retry_on_openai_errors_async_creation(self) -> None:
        """Test that the async decorator is created correctly."""
        # Create a simple mock to replace retry without needing tenacity internals
        mock_decorated = MagicMock()

        with patch("codestory.llm.backoff.retry") as mock_retry:
            # Configure the mock to return our test function
            mock_retry.return_value = lambda f: mock_decorated

            # Call the async decorator factory
            decorator = retry_on_openai_errors_async(
                max_retries=5,
                retry_backoff_factor=3.0,
                operation_type=OperationType.EMBEDDING,
            )

            # Apply the decorator to a test function
            decorated = decorator(lambda: None)

            # Verify the decorator works as expected
            assert decorated is mock_decorated  # The function is decorated
            assert mock_retry.call_count == 1  # Retry was called once to create decorator
