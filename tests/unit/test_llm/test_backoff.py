from typing import Any

'Tests for OpenAI client retry and backoff logic.'
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


@pytest.fixture(autouse=True)
def mock_all_prometheus() -> None:
    """Mock all Prometheus metrics objects before any module imports."""
    with patch('prometheus_client.Counter') as mock_counter, patch('prometheus_client.Gauge') as mock_gauge, patch('prometheus_client.Histogram') as mock_histogram, patch('prometheus_client.registry.REGISTRY._names_to_collectors', {}), patch('codestory.llm.metrics.record_retry'):
        mock_labels = MagicMock()
        mock_counter.return_value.labels = mock_labels
        mock_gauge.return_value.labels = mock_labels
        mock_histogram.return_value.labels = mock_labels
        yield

class TestRetryFunctions:
    """Tests for retry utility functions."""

    def test_get_retry_after(self: Any) -> None:
        """Test get_retry_after function."""
        retry_state = MagicMock()
        exception = RateLimitError('Rate limit exceeded', retry_after=30)
        retry_state.outcome.exception.return_value = exception
        result = get_retry_after(retry_state)
        assert result == 30
        exception = RateLimitError('Rate limit exceeded', retry_after=120)
        retry_state.outcome.exception.return_value = exception
        result = get_retry_after(retry_state)
        assert result == 60
        exception = RateLimitError('Rate limit exceeded')
        retry_state.outcome.exception.return_value = exception
        result = get_retry_after(retry_state)
        assert result is None

    def test_before_retry_callback(self: Any) -> None:
        """Test before_retry_callback function."""
        retry_state = MagicMock()
        retry_state.attempt_number = 2
        retry_state.kwargs = {'_operation_type': OperationType.CHAT, 'model': 'gpt-4o'}
        retry_state.next_action.sleep = 4.0
        exception = RateLimitError('Rate limit exceeded')
        retry_state.outcome.exception.return_value = exception
        with patch('codestory.llm.backoff.record_retry') as mock_record:
            before_retry_callback(retry_state)
            mock_record.assert_called_once_with(OperationType.CHAT, 'gpt-4o')
        retry_state.kwargs = {'model': 'gpt-4o'}
        with patch('codestory.llm.backoff.record_retry') as mock_record:
            before_retry_callback(retry_state)
            mock_record.assert_not_called()

class TestRetryDecorators:
    """Tests for retry decorators."""

    def test_retry_on_openai_errors(self: Any) -> None:
        """Test the retry_on_openai_errors decorator."""
        mock_func = MagicMock()
        mock_func.side_effect = [RateLimitError('Rate limit exceeded'), ServiceUnavailableError('Service unavailable'), 'Success Result']
        with patch('codestory.llm.backoff.retry') as mock_retry:
            mock_retry.return_value = lambda f: f
            decorator = retry_on_openai_errors(max_retries=3, operation_type=OperationType.CHAT)
            decorated_func = decorator(mock_func)
            try:
                decorated_func(model='gpt-4o')
                pytest.fail('Expected RateLimitError')
            except RateLimitError:
                pass
            try:
                decorated_func(model='gpt-4o')
                pytest.fail('Expected ServiceUnavailableError')
            except ServiceUnavailableError:
                pass
            result = decorated_func(model='gpt-4o')
            assert result == 'Success Result'
            assert '_operation_type' in mock_func.call_args[1]
            assert mock_func.call_args[1]['_operation_type'] == OperationType.CHAT

    def test_exception_conversion_rate_limit(self: Any) -> None:
        """Test conversion of RateLimitError."""
        with patch('codestory.llm.backoff.retry') as mock_retry:
            mock_retry.return_value = lambda f: f

            def test_func() -> None:
                raise openai.RateLimitError(message='Rate limit exceeded', response=MagicMock(), body=None)
            decorated_func = retry_on_openai_errors(max_retries=1)(test_func)
            with pytest.raises(RateLimitError):
                decorated_func()

    def test_exception_conversion_api_connection(self: Any) -> None:
        """Test conversion of APIConnectionError."""
        with patch('codestory.llm.backoff.retry') as mock_retry:
            mock_retry.return_value = lambda f: f

            def test_func() -> None:
                raise openai.APIConnectionError(message='Connection error', request=MagicMock())
            decorated_func = retry_on_openai_errors(max_retries=1)(test_func)
            with pytest.raises(ServiceUnavailableError):
                decorated_func()

    def test_exception_conversion_timeout(self: Any) -> None:
        """Test TimeoutError conversion directly."""
        with patch('codestory.llm.backoff.retry') as mock_retry:
            mock_retry.return_value = lambda f: f

            class MockAPITimeoutError(Exception):

                def __init__(self) -> None:
                    self.message = 'Request timed out'
                    super().__init__(self.message)

            def test_func() -> None:
                with patch('openai.APITimeoutError', MockAPITimeoutError):
                    raise MockAPITimeoutError()
            with patch('openai.APITimeoutError', MockAPITimeoutError):
                decorated_func = retry_on_openai_errors(max_retries=1)(test_func)
                with pytest.raises(TimeoutError) as exc_info:
                    decorated_func()
                assert 'API request timed out' in str(exc_info.value)
                assert 'Request timed out' in str(exc_info.value)

    def test_exception_conversion_context_length(self: Any) -> None:
        """Test conversion of BadRequestError for context length."""
        with patch('codestory.llm.backoff.retry') as mock_retry:
            mock_retry.return_value = lambda f: f

            def test_func() -> None:
                raise openai.BadRequestError(message='Input context length exceeded maximum context length', response=MagicMock(), body=None)
            decorated_func = retry_on_openai_errors(max_retries=1)(test_func)
            with pytest.raises(ContextLengthError):
                decorated_func()

    def test_retry_on_openai_errors_retry_after(self: Any) -> None:
        """Test that retry_after is extracted from headers."""
        with patch('codestory.llm.backoff.retry') as mock_retry:
            mock_retry.return_value = lambda f: f

            def test_retry_after() -> None:
                e = openai.RateLimitError(message='Rate limit exceeded', response=MagicMock(), body=None)
                e.headers = {'retry-after': '30'}
                raise e
            decorated_func = retry_on_openai_errors(max_retries=1)(test_retry_after)
            with pytest.raises(RateLimitError) as exc_info:
                decorated_func()
            assert exc_info.value.retry_after == 30

    def test_retry_on_openai_errors_async_creation(self: Any) -> None:
        """Test that the async decorator is created correctly."""
        mock_decorated = MagicMock()
        with patch('codestory.llm.backoff.retry') as mock_retry:
            mock_retry.return_value = lambda f: mock_decorated
            decorator = retry_on_openai_errors_async(max_retries=5, retry_backoff_factor=3.0, operation_type=OperationType.EMBEDDING)
            decorated = decorator(lambda: None)
            assert decorated is mock_decorated
            assert mock_retry.call_count == 1