from typing import Any

"Tests for OpenAI client metrics collection."
from unittest.mock import MagicMock, call, patch

import pytest

from codestory.llm.metrics import OperationType


@pytest.fixture(autouse=True)
def mock_all_metrics_objects() -> None:
    """Mock all Prometheus metrics objects before any module imports."""
    with patch("prometheus_client.Counter") as mock_counter, patch(
        "prometheus_client.Gauge"
    ) as mock_gauge, patch("prometheus_client.Histogram") as mock_histogram, patch(
        "prometheus_client.registry.REGISTRY._names_to_collectors", {}
    ):
        mock_labels = MagicMock()
        mock_counter.return_value.labels = mock_labels
        mock_gauge.return_value.labels = mock_labels
        mock_histogram.return_value.labels = mock_labels
        from codestory.llm.metrics import (
            CURRENT_REQUESTS,
            ERROR_COUNT,
            REQUEST_COUNT,
            REQUEST_DURATION,
            RETRY_COUNT,
            TOKEN_USAGE,
            instrument_async_request,
            instrument_request,
            record_error,
            record_request,
            record_retry,
        )

        metrics_objects = {
            "ERROR_COUNT": ERROR_COUNT,
            "REQUEST_COUNT": REQUEST_COUNT,
            "REQUEST_DURATION": REQUEST_DURATION,
            "RETRY_COUNT": RETRY_COUNT,
            "TOKEN_USAGE": TOKEN_USAGE,
            "CURRENT_REQUESTS": CURRENT_REQUESTS,
            "instrument_async_request": instrument_async_request,
            "instrument_request": instrument_request,
            "record_error": record_error,
            "record_request": record_request,
            "record_retry": record_retry,
        }
        yield metrics_objects


class TestMetricsFunctions:
    """Tests for metrics utility functions."""

    def test_record_request(self: Any, mock_all_metrics_objects: Any) -> None:
        """Test record_request function."""
        record_request = mock_all_metrics_objects["record_request"]
        request_count = mock_all_metrics_objects["REQUEST_COUNT"]
        request_duration = mock_all_metrics_objects["REQUEST_DURATION"]
        with patch.object(request_count, "labels") as mock_count_labels, patch.object(
            request_duration, "labels"
        ) as mock_duration_labels:
            mock_count_labels.return_value.inc = MagicMock()
            mock_duration_labels.return_value.observe = MagicMock()
            record_request(
                operation=OperationType.CHAT,
                model="gpt-4o",
                status="success",
                duration=1.5,
            )
            mock_count_labels.assert_called_once_with(
                operation="chat", model="gpt-4o", status="success"
            )
            mock_count_labels.return_value.inc.assert_called_once()
            mock_duration_labels.assert_called_once_with(
                operation="chat", model="gpt-4o"
            )
            mock_duration_labels.return_value.observe.assert_called_once_with(1.5)

    def test_record_request_with_tokens(
        self: Any, mock_all_metrics_objects: Any
    ) -> None:
        """Test record_request function with token usage."""
        record_request = mock_all_metrics_objects["record_request"]
        request_count = mock_all_metrics_objects["REQUEST_COUNT"]
        request_duration = mock_all_metrics_objects["REQUEST_DURATION"]
        token_usage = mock_all_metrics_objects["TOKEN_USAGE"]
        with patch.object(request_count, "labels") as mock_count_labels, patch.object(
            request_duration, "labels"
        ) as mock_duration_labels, patch.object(
            token_usage, "labels"
        ) as mock_token_labels:
            mock_count_labels.return_value.inc = MagicMock()
            mock_duration_labels.return_value.observe = MagicMock()
            mock_token_labels.return_value.inc = MagicMock()
            record_request(
                operation=OperationType.CHAT,
                model="gpt-4o",
                status="success",
                duration=1.5,
                tokens={"prompt": 100, "completion": 50, "total": 150},
            )
            mock_count_labels.assert_called_once()
            mock_duration_labels.assert_called_once()
            assert mock_token_labels.call_count == 3
            mock_token_labels.assert_has_calls(
                [
                    call(operation="chat", model="gpt-4o", token_type="prompt"),
                    call(operation="chat", model="gpt-4o", token_type="completion"),
                    call(operation="chat", model="gpt-4o", token_type="total"),
                ],
                any_order=True,
            )
            mock_token_labels.return_value.inc.assert_has_calls(
                [call(100), call(50), call(150)], any_order=True
            )

    def test_record_error(self: Any, mock_all_metrics_objects: Any) -> None:
        """Test record_error function."""
        record_error = mock_all_metrics_objects["record_error"]
        error_count = mock_all_metrics_objects["ERROR_COUNT"]
        with patch.object(error_count, "labels") as mock_error_labels:
            mock_error_labels.return_value.inc = MagicMock()
            record_error(
                operation=OperationType.EMBEDDING,
                model="text-embedding-3-small",
                error_type="RateLimitError",
            )
            mock_error_labels.assert_called_once_with(
                operation="embedding",
                model="text-embedding-3-small",
                error_type="RateLimitError",
            )
            mock_error_labels.return_value.inc.assert_called_once()

    def test_record_retry(self: Any, mock_all_metrics_objects: Any) -> None:
        """Test record_retry function."""
        record_retry = mock_all_metrics_objects["record_retry"]
        retry_count = mock_all_metrics_objects["RETRY_COUNT"]
        with patch.object(retry_count, "labels") as mock_retry_labels:
            mock_retry_labels.return_value.inc = MagicMock()
            record_retry(operation=OperationType.COMPLETION, model="gpt-4o")
            mock_retry_labels.assert_called_once_with(
                operation="completion", model="gpt-4o"
            )
            mock_retry_labels.return_value.inc.assert_called_once()


class TestInstrumentRequestDecorator:
    """Tests for the instrument_request decorator."""

    def test_instrument_request_success(
        self: Any, mock_all_metrics_objects: Any
    ) -> None:
        """Test instrument_request decorator with successful response."""
        instrument_request = mock_all_metrics_objects["instrument_request"]
        current_requests = mock_all_metrics_objects["CURRENT_REQUESTS"]
        mock_function = MagicMock()
        mock_function.return_value = MagicMock(
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        decorated_function = instrument_request(OperationType.CHAT)(mock_function)
        with patch.object(current_requests, "labels") as mock_current, patch(
            "codestory.llm.metrics.record_request"
        ) as mock_record:
            mock_current.return_value.inc = MagicMock()
            mock_current.return_value.dec = MagicMock()
            decorated_function(model="gpt-4o", arg1="value1")
            mock_function.assert_called_once_with(model="gpt-4o", arg1="value1")
            mock_current.assert_called_with(operation="chat", model="gpt-4o")
            mock_current.return_value.inc.assert_called_once()
            mock_current.return_value.dec.assert_called_once()
            mock_record.assert_called_once()
            args, kwargs = mock_record.call_args
            assert kwargs["operation"] == OperationType.CHAT
            assert kwargs["model"] == "gpt-4o"
            assert kwargs["status"] == "success"
            assert "duration" in kwargs
            assert kwargs["tokens"] == {"prompt": 100, "completion": 50, "total": 150}

    def test_instrument_request_error(self: Any, mock_all_metrics_objects: Any) -> None:
        """Test instrument_request decorator with an error response."""
        instrument_request = mock_all_metrics_objects["instrument_request"]
        current_requests = mock_all_metrics_objects["CURRENT_REQUESTS"]
        mock_function = MagicMock()
        mock_function.side_effect = ValueError("Test error")
        decorated_function = instrument_request(OperationType.EMBEDDING)(mock_function)
        with patch.object(current_requests, "labels") as mock_current, patch(
            "codestory.llm.metrics.record_request"
        ) as mock_record_req, patch(
            "codestory.llm.metrics.record_error"
        ) as mock_record_err:
            mock_current.return_value.inc = MagicMock()
            mock_current.return_value.dec = MagicMock()
            with pytest.raises(ValueError):
                decorated_function(model="text-embedding-3-small")
            mock_function.assert_called_once()
            mock_current.assert_called_with(
                operation="embedding", model="text-embedding-3-small"
            )
            mock_current.return_value.inc.assert_called_once()
            mock_current.return_value.dec.assert_called_once()
            mock_record_req.assert_called_once()
            args, kwargs = mock_record_req.call_args
            assert kwargs["operation"] == OperationType.EMBEDDING
            assert kwargs["model"] == "text-embedding-3-small"
            assert kwargs["status"] == "error"
            assert "duration" in kwargs
            mock_record_err.assert_called_once()
            args, kwargs = mock_record_err.call_args
            assert kwargs["operation"] == OperationType.EMBEDDING
            assert kwargs["model"] == "text-embedding-3-small"
            assert kwargs["error_type"] == "ValueError"


class TestInstrumentAsyncRequestDecorator:
    """Tests for the instrument_async_request decorator."""

    @pytest.mark.asyncio
    async def test_instrument_async_request_success(
        self: Any, mock_all_metrics_objects: Any
    ) -> None:
        """Test instrument_async_request decorator with successful response."""
        instrument_async_request = mock_all_metrics_objects["instrument_async_request"]
        current_requests = mock_all_metrics_objects["CURRENT_REQUESTS"]
        mock_function = MagicMock()

        async def mock_coro(*args, **kwargs):
            return MagicMock(
                usage=MagicMock(
                    prompt_tokens=100, completion_tokens=50, total_tokens=150
                )
            )

        mock_function.side_effect = mock_coro
        decorated_function = instrument_async_request(OperationType.CHAT)(mock_function)
        with patch.object(current_requests, "labels") as mock_current, patch(
            "codestory.llm.metrics.record_request"
        ) as mock_record:
            mock_current.return_value.inc = MagicMock()
            mock_current.return_value.dec = MagicMock()
            await decorated_function(model="gpt-4o", arg1="value1")
            mock_function.assert_called_once_with(model="gpt-4o", arg1="value1")
            mock_current.assert_called_with(operation="chat", model="gpt-4o")
            mock_current.return_value.inc.assert_called_once()
            mock_current.return_value.dec.assert_called_once()
            mock_record.assert_called_once()
            args, kwargs = mock_record.call_args
            assert kwargs["operation"] == OperationType.CHAT
            assert kwargs["model"] == "gpt-4o"
            assert kwargs["status"] == "success"
            assert "duration" in kwargs
            assert kwargs["tokens"] == {"prompt": 100, "completion": 50, "total": 150}

    @pytest.mark.asyncio
    async def test_instrument_async_request_error(
        self: Any, mock_all_metrics_objects: Any
    ) -> None:
        """Test instrument_async_request decorator with an error response."""
        instrument_async_request = mock_all_metrics_objects["instrument_async_request"]
        current_requests = mock_all_metrics_objects["CURRENT_REQUESTS"]
        mock_function = MagicMock()

        async def mock_coro(*args, **kwargs) -> None:
            raise ValueError("Test error")

        mock_function.side_effect = mock_coro
        decorated_function = instrument_async_request(OperationType.EMBEDDING)(
            mock_function
        )
        with patch.object(current_requests, "labels") as mock_current, patch(
            "codestory.llm.metrics.record_request"
        ) as mock_record_req, patch(
            "codestory.llm.metrics.record_error"
        ) as mock_record_err:
            mock_current.return_value.inc = MagicMock()
            mock_current.return_value.dec = MagicMock()
            with pytest.raises(ValueError):
                await decorated_function(model="text-embedding-3-small")
            mock_function.assert_called_once()
            mock_current.assert_called_with(
                operation="embedding", model="text-embedding-3-small"
            )
            mock_current.return_value.inc.assert_called_once()
            mock_current.return_value.dec.assert_called_once()
            mock_record_req.assert_called_once()
            args, kwargs = mock_record_req.call_args
            assert kwargs["operation"] == OperationType.EMBEDDING
            assert kwargs["model"] == "text-embedding-3-small"
            assert kwargs["status"] == "error"
            assert "duration" in kwargs
            mock_record_err.assert_called_once()
            args, kwargs = mock_record_err.call_args
            assert kwargs["operation"] == OperationType.EMBEDDING
            assert kwargs["model"] == "text-embedding-3-small"
            assert kwargs["error_type"] == "ValueError"
