"""Metrics collection for OpenAI client.

This module provides Prometheus metrics for monitoring OpenAI API usage,
including request counts, latencies, token usage, and errors.
"""
import functools
import time
from collections.abc import Callable, Iterable, Sequence
from contextlib import contextmanager
from enum import Enum
from typing import Any, Protocol, TypeVar, Union, cast
from prometheus_client import Counter, Gauge, Histogram
from prometheus_client.registry import REGISTRY, CollectorRegistry
F = TypeVar('F', bound=Callable[..., Any])

class CounterLike(Protocol):
    """Protocol for counter-like objects."""

    def inc(self, amount: float=1.0) -> None:
        """Increment counter."""
        ...

    def labels(self, **kwargs: Any) -> 'CounterLike':
        """Get labeled instance."""
        ...

class GaugeLike(Protocol):
    """Protocol for gauge-like objects."""

    def inc(self, amount: float=1.0) -> None:
        """Increment gauge."""
        ...

    def dec(self, amount: float=1.0) -> None:
        """Decrement gauge."""
        ...

    def set(self, value: float) -> None:
        """Set gauge value."""
        ...

    def labels(self, **kwargs: Any) -> 'GaugeLike':
        """Get labeled instance."""
        ...

class HistogramLike(Protocol):
    """Protocol for histogram-like objects."""

    def observe(self, amount: float, exemplar: Any=None) -> None:
        """Record an observation."""
        ...

    def labels(self, **kwargs: Any) -> 'HistogramLike':
        """Get labeled instance."""
        ...

class OperationType(str, Enum):
    """Types of operations for metrics collection."""
    COMPLETION = 'completion'
    CHAT = 'chat'
    EMBEDDING = 'embedding'

def _get_or_create_counter(name: str, description: str, labels: Iterable[str] | None=None) -> CounterLike:
    """Get or create a Counter metric, handling registration conflicts."""
    try:
        return Counter(name, description, labels or [])
    except ValueError:
        for collector in list(REGISTRY._names_to_collectors.values()):
            if isinstance(collector, Counter) and hasattr(collector, '_name') and (collector._name == name):
                return collector
        private_registry = CollectorRegistry()
        return Counter(name, description, labels or [], registry=private_registry)

def _get_or_create_gauge(name: str, description: str, labels: Iterable[str] | None=None) -> GaugeLike:
    """Get or create a Gauge metric, handling registration conflicts."""
    try:
        return Gauge(name, description, labels or [])
    except ValueError:
        for collector in list(REGISTRY._names_to_collectors.values()):
            if isinstance(collector, Gauge) and hasattr(collector, '_name') and (collector._name == name):
                return collector
        private_registry = CollectorRegistry()
        return Gauge(name, description, labels or [], registry=private_registry)

def _get_or_create_histogram(name: str, description: str, labels: Iterable[str] | None=None, buckets: Sequence[Union[float, str]] | None=None) -> HistogramLike:
    """Get or create a Histogram metric, handling registration conflicts."""
    histogram_buckets = buckets if buckets is not None else ()
    try:
        return Histogram(name, description, labels or [], buckets=histogram_buckets)
    except ValueError:
        for collector in list(REGISTRY._names_to_collectors.values()):
            if isinstance(collector, Histogram) and hasattr(collector, '_name') and (collector._name == name):
                return collector
        private_registry = CollectorRegistry()
        return Histogram(name, description, labels or [], buckets=histogram_buckets, registry=private_registry)
REQUEST_COUNT: CounterLike = _get_or_create_counter('openai_request_total', 'Total number of requests to OpenAI API', ['operation', 'model', 'status'])
ERROR_COUNT: CounterLike = _get_or_create_counter('openai_error_total', 'Total number of errors from OpenAI API', ['operation', 'model', 'error_type'])
RETRY_COUNT: CounterLike = _get_or_create_counter('openai_retry_total', 'Total number of retried requests to OpenAI API', ['operation', 'model'])
REQUEST_DURATION: HistogramLike = _get_or_create_histogram('openai_request_duration_seconds', 'Time taken for OpenAI API requests', ['operation', 'model'], buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0))
TOKEN_USAGE: CounterLike = _get_or_create_counter('openai_token_usage_total', 'Token usage for OpenAI API', ['operation', 'model', 'token_type'])
CURRENT_REQUESTS: GaugeLike = _get_or_create_gauge('openai_current_requests', 'Number of currently executing OpenAI API requests', ['operation', 'model'])

def record_request(operation: OperationType, model: str, status: str, duration: float, tokens: dict[str, int] | None=None) -> None:
    """Record metrics for an OpenAI API request.

    Args:
        operation: Type of operation (completion, chat, embedding)
        model: Model used for the request
        status: Status of the request (success, error)
        duration: Duration of the request in seconds
        tokens: Token usage information (optional)
    """
    REQUEST_COUNT.labels(operation=operation.value, model=model, status=status).inc()
    REQUEST_DURATION.labels(operation=operation.value, model=model).observe(duration)
    if tokens:
        for token_type, count in tokens.items():
            TOKEN_USAGE.labels(operation=operation.value, model=model, token_type=token_type).inc(count)

def record_error(operation: OperationType, model: str, error_type: str) -> None:
    """Record metrics for an OpenAI API error.

    Args:
        operation: Type of operation (completion, chat, embedding)
        model: Model used for the request
        error_type: Type of error that occurred
    """
    ERROR_COUNT.labels(operation=operation.value, model=model, error_type=error_type).inc()

def record_retry(operation: OperationType, model: str) -> None:
    """Record metrics for an OpenAI API retry.

    Args:
        operation: Type of operation (completion, chat, embedding)
        model: Model used for the request
    """
    RETRY_COUNT.labels(operation=operation.value, model=model).inc()

def instrument_request(operation: OperationType) -> Callable[[F], F]:
    """Decorator to instrument OpenAI API requests with metrics.

    Args:
        operation: Type of operation (completion, chat, embedding)

    Returns:
        Decorator function that wraps an API call with metrics
    """

    def decorator(func: F) -> F:

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            model = kwargs.get('model', 'unknown')
            CURRENT_REQUESTS.labels(operation=operation.value, model=model).inc()
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                tokens = None
                if hasattr(result, 'usage'):
                    usage = result.usage
                    if usage:
                        tokens = {'prompt': usage.prompt_tokens, 'completion': usage.completion_tokens or 0, 'total': usage.total_tokens}
                record_request(operation=operation, model=model, status='success', duration=duration, tokens=tokens)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_type = type(e).__name__
                record_request(operation=operation, model=model, status='error', duration=duration)
                record_error(operation=operation, model=model, error_type=error_type)
                raise
            finally:
                CURRENT_REQUESTS.labels(operation=operation.value, model=model).dec()
        return cast('F', wrapper)
    return decorator

def instrument_async_request(operation: OperationType) -> Callable[[F], F]:
    """Decorator to instrument async OpenAI API requests with metrics.

    Args:
        operation: Type of operation (completion, chat, embedding)

    Returns:
        Decorator function that wraps an async API call with metrics
    """

    def decorator(func: F) -> F:

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> None:
            model = kwargs.get('model', 'unknown')
            CURRENT_REQUESTS.labels(operation=operation.value, model=model).inc()
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                tokens = None
                if hasattr(result, 'usage'):
                    usage = result.usage
                    if usage:
                        tokens = {'prompt': usage.prompt_tokens, 'completion': usage.completion_tokens or 0, 'total': usage.total_tokens}
                record_request(operation=operation, model=model, status='success', duration=duration, tokens=tokens)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_type = type(e).__name__
                record_request(operation=operation, model=model, status='error', duration=duration)
                record_error(operation=operation, model=model, error_type=error_type)
                raise
            finally:
                CURRENT_REQUESTS.labels(operation=operation.value, model=model).dec()
        return cast('F', wrapper)
    return decorator