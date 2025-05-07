"""Tests for OpenAI client metrics collection."""

from unittest.mock import MagicMock, call, patch

import pytest

from src.codestory.llm.metrics import (
    ERROR_COUNT,
    REQUEST_COUNT,
    REQUEST_DURATION,
    RETRY_COUNT,
    TOKEN_USAGE,
    OperationType,
    instrument_async_request,
    instrument_request,
    record_error,
    record_request,
    record_retry,
)


class TestMetricsFunctions:
    """Tests for metrics utility functions."""
    
    def test_record_request(self):
        """Test record_request function."""
        with patch.object(REQUEST_COUNT, "labels") as mock_count_labels, \
             patch.object(REQUEST_DURATION, "labels") as mock_duration_labels:
            
            # Configure mocks
            mock_count_labels.return_value.inc = MagicMock()
            mock_duration_labels.return_value.observe = MagicMock()
            
            # Call function without tokens
            record_request(
                operation=OperationType.CHAT,
                model="gpt-4o",
                status="success",
                duration=1.5
            )
            
            # Verify metrics were recorded
            mock_count_labels.assert_called_once_with(
                operation="chat", model="gpt-4o", status="success"
            )
            mock_count_labels.return_value.inc.assert_called_once()
            
            mock_duration_labels.assert_called_once_with(
                operation="chat", model="gpt-4o"
            )
            mock_duration_labels.return_value.observe.assert_called_once_with(1.5)
    
    def test_record_request_with_tokens(self):
        """Test record_request function with token usage."""
        with patch.object(REQUEST_COUNT, "labels") as mock_count_labels, \
             patch.object(REQUEST_DURATION, "labels") as mock_duration_labels, \
             patch.object(TOKEN_USAGE, "labels") as mock_token_labels:
            
            # Configure mocks
            mock_count_labels.return_value.inc = MagicMock()
            mock_duration_labels.return_value.observe = MagicMock()
            mock_token_labels.return_value.inc = MagicMock()
            
            # Call function with tokens
            record_request(
                operation=OperationType.CHAT,
                model="gpt-4o",
                status="success",
                duration=1.5,
                tokens={
                    "prompt": 100,
                    "completion": 50,
                    "total": 150
                }
            )
            
            # Verify metrics were recorded including tokens
            mock_count_labels.assert_called_once()
            mock_duration_labels.assert_called_once()
            
            # Check token usage metrics
            assert mock_token_labels.call_count == 3
            
            # Verify each token type was recorded
            mock_token_labels.assert_has_calls([
                call(operation="chat", model="gpt-4o", token_type="prompt"),
                call(operation="chat", model="gpt-4o", token_type="completion"),
                call(operation="chat", model="gpt-4o", token_type="total")
            ], any_order=True)
            
            # Check that token counts were used
            mock_token_labels.return_value.inc.assert_has_calls([
                call(100),  # prompt tokens
                call(50),   # completion tokens
                call(150)   # total tokens
            ], any_order=True)
    
    def test_record_error(self):
        """Test record_error function."""
        with patch.object(ERROR_COUNT, "labels") as mock_error_labels:
            # Configure mock
            mock_error_labels.return_value.inc = MagicMock()
            
            # Call function
            record_error(
                operation=OperationType.EMBEDDING,
                model="text-embedding-3-small",
                error_type="RateLimitError"
            )
            
            # Verify error was recorded
            mock_error_labels.assert_called_once_with(
                operation="embedding",
                model="text-embedding-3-small",
                error_type="RateLimitError"
            )
            mock_error_labels.return_value.inc.assert_called_once()
    
    def test_record_retry(self):
        """Test record_retry function."""
        with patch.object(RETRY_COUNT, "labels") as mock_retry_labels:
            # Configure mock
            mock_retry_labels.return_value.inc = MagicMock()
            
            # Call function
            record_retry(
                operation=OperationType.COMPLETION,
                model="gpt-4o"
            )
            
            # Verify retry was recorded
            mock_retry_labels.assert_called_once_with(
                operation="completion",
                model="gpt-4o"
            )
            mock_retry_labels.return_value.inc.assert_called_once()


class TestInstrumentRequestDecorator:
    """Tests for the instrument_request decorator."""

    def test_instrument_request_success(self):
        """Test instrument_request decorator with successful response."""
        # Create a mock function that returns a result with usage info
        mock_function = MagicMock()
        mock_function.return_value = MagicMock(
            usage=MagicMock(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
        )
        
        # Apply the decorator
        decorated_function = instrument_request(OperationType.CHAT)(mock_function)
        
        # Patch the metrics functions
        with patch("src.codestory.llm.metrics.CURRENT_REQUESTS.labels") as mock_current, \
             patch("src.codestory.llm.metrics.record_request") as mock_record:
            
            # Configure the mock
            mock_current.return_value.inc = MagicMock()
            mock_current.return_value.dec = MagicMock()
            
            # Call the decorated function
            result = decorated_function(model="gpt-4o", arg1="value1")
            
            # Verify the original function was called with the args
            mock_function.assert_called_once_with(model="gpt-4o", arg1="value1")
            
            # Verify the current requests counter was incremented and decremented
            mock_current.assert_called_with(operation="chat", model="gpt-4o")
            mock_current.return_value.inc.assert_called_once()
            mock_current.return_value.dec.assert_called_once()
            
            # Verify the record_request function was called with tokens
            mock_record.assert_called_once()
            args, kwargs = mock_record.call_args
            assert kwargs["operation"] == OperationType.CHAT
            assert kwargs["model"] == "gpt-4o"
            assert kwargs["status"] == "success"
            assert "duration" in kwargs
            
            # Check token info was extracted
            assert kwargs["tokens"] == {
                "prompt": 100,
                "completion": 50,
                "total": 150
            }
    
    def test_instrument_request_error(self):
        """Test instrument_request decorator with an error response."""
        # Create a mock function that raises an exception
        mock_function = MagicMock()
        mock_function.side_effect = ValueError("Test error")
        
        # Apply the decorator
        decorated_function = instrument_request(OperationType.EMBEDDING)(mock_function)
        
        # Patch the metrics functions
        with patch("src.codestory.llm.metrics.CURRENT_REQUESTS.labels") as mock_current, \
             patch("src.codestory.llm.metrics.record_request") as mock_record_req, \
             patch("src.codestory.llm.metrics.record_error") as mock_record_err:
            
            # Configure the mock
            mock_current.return_value.inc = MagicMock()
            mock_current.return_value.dec = MagicMock()
            
            # Call the decorated function and expect it to raise the same error
            with pytest.raises(ValueError):
                decorated_function(model="text-embedding-3-small")
            
            # Verify the original function was called
            mock_function.assert_called_once()
            
            # Verify the current requests counter was incremented and decremented
            mock_current.assert_called_with(operation="embedding", model="text-embedding-3-small")
            mock_current.return_value.inc.assert_called_once()
            mock_current.return_value.dec.assert_called_once()
            
            # Verify the record_request function was called with error status
            mock_record_req.assert_called_once()
            args, kwargs = mock_record_req.call_args
            assert kwargs["operation"] == OperationType.EMBEDDING
            assert kwargs["model"] == "text-embedding-3-small"
            assert kwargs["status"] == "error"
            assert "duration" in kwargs
            
            # Verify the record_error function was called
            mock_record_err.assert_called_once()
            args, kwargs = mock_record_err.call_args
            assert kwargs["operation"] == OperationType.EMBEDDING
            assert kwargs["model"] == "text-embedding-3-small"
            assert kwargs["error_type"] == "ValueError"


class TestInstrumentAsyncRequestDecorator:
    """Tests for the instrument_async_request decorator."""
    
    @pytest.mark.asyncio
    async def test_instrument_async_request_success(self):
        """Test instrument_async_request decorator with successful response."""
        # Create a mock async function that returns a result with usage info
        mock_function = MagicMock()
        
        # Configure the mock to work with await
        async def mock_coro(*args, **kwargs):
            return MagicMock(
                usage=MagicMock(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150
                )
            )
        
        mock_function.side_effect = mock_coro
        
        # Apply the decorator
        decorated_function = instrument_async_request(OperationType.CHAT)(mock_function)
        
        # Patch the metrics functions
        with patch("src.codestory.llm.metrics.CURRENT_REQUESTS.labels") as mock_current, \
             patch("src.codestory.llm.metrics.record_request") as mock_record:
            
            # Configure the mock
            mock_current.return_value.inc = MagicMock()
            mock_current.return_value.dec = MagicMock()
            
            # Call the decorated function
            result = await decorated_function(model="gpt-4o", arg1="value1")
            
            # Verify the original function was called with the args
            mock_function.assert_called_once_with(model="gpt-4o", arg1="value1")
            
            # Verify the current requests counter was incremented and decremented
            mock_current.assert_called_with(operation="chat", model="gpt-4o")
            mock_current.return_value.inc.assert_called_once()
            mock_current.return_value.dec.assert_called_once()
            
            # Verify the record_request function was called with tokens
            mock_record.assert_called_once()
            args, kwargs = mock_record.call_args
            assert kwargs["operation"] == OperationType.CHAT
            assert kwargs["model"] == "gpt-4o"
            assert kwargs["status"] == "success"
            assert "duration" in kwargs
            
            # Check token info was extracted
            assert kwargs["tokens"] == {
                "prompt": 100,
                "completion": 50,
                "total": 150
            }
    
    @pytest.mark.asyncio
    async def test_instrument_async_request_error(self):
        """Test instrument_async_request decorator with an error response."""
        # Create a mock async function that raises an exception
        mock_function = MagicMock()
        
        # Configure the mock to work with await
        async def mock_coro(*args, **kwargs):
            raise ValueError("Test error")
        
        mock_function.side_effect = mock_coro
        
        # Apply the decorator
        decorated_function = instrument_async_request(OperationType.EMBEDDING)(mock_function)
        
        # Patch the metrics functions
        with patch("src.codestory.llm.metrics.CURRENT_REQUESTS.labels") as mock_current, \
             patch("src.codestory.llm.metrics.record_request") as mock_record_req, \
             patch("src.codestory.llm.metrics.record_error") as mock_record_err:
            
            # Configure the mock
            mock_current.return_value.inc = MagicMock()
            mock_current.return_value.dec = MagicMock()
            
            # Call the decorated function and expect it to raise the same error
            with pytest.raises(ValueError):
                await decorated_function(model="text-embedding-3-small")
            
            # Verify the original function was called
            mock_function.assert_called_once()
            
            # Verify the current requests counter was incremented and decremented
            mock_current.assert_called_with(operation="embedding", model="text-embedding-3-small")
            mock_current.return_value.inc.assert_called_once()
            mock_current.return_value.dec.assert_called_once()
            
            # Verify the record_request function was called with error status
            mock_record_req.assert_called_once()
            args, kwargs = mock_record_req.call_args
            assert kwargs["operation"] == OperationType.EMBEDDING
            assert kwargs["model"] == "text-embedding-3-small"
            assert kwargs["status"] == "error"
            assert "duration" in kwargs
            
            # Verify the record_error function was called
            mock_record_err.assert_called_once()
            args, kwargs = mock_record_err.call_args
            assert kwargs["operation"] == OperationType.EMBEDDING
            assert kwargs["model"] == "text-embedding-3-small"
            assert kwargs["error_type"] == "ValueError"