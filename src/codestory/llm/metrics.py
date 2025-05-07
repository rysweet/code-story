"""Metrics collection for OpenAI client.

This module provides Prometheus metrics for monitoring OpenAI API usage,
including request counts, latencies, token usage, and errors.
"""

import time
import functools
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from prometheus_client import Counter, Gauge, Histogram

# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])


class OperationType(str, Enum):
    """Types of operations for metrics collection."""
    
    COMPLETION = "completion"
    CHAT = "chat"
    EMBEDDING = "embedding"


# Prometheus metrics
REQUEST_COUNT = Counter(
    "openai_request_total",
    "Total number of requests to OpenAI API",
    ["operation", "model", "status"]
)

ERROR_COUNT = Counter(
    "openai_error_total",
    "Total number of errors from OpenAI API",
    ["operation", "model", "error_type"]
)

RETRY_COUNT = Counter(
    "openai_retry_total",
    "Total number of retried requests to OpenAI API",
    ["operation", "model"]
)

REQUEST_DURATION = Histogram(
    "openai_request_duration_seconds",
    "Time taken for OpenAI API requests",
    ["operation", "model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
)

TOKEN_USAGE = Counter(
    "openai_token_usage_total",
    "Token usage for OpenAI API",
    ["operation", "model", "token_type"]
)

CURRENT_REQUESTS = Gauge(
    "openai_current_requests",
    "Number of currently executing OpenAI API requests",
    ["operation", "model"]
)


def record_request(
    operation: OperationType,
    model: str,
    status: str,
    duration: float,
    tokens: Optional[Dict[str, int]] = None,
) -> None:
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
            TOKEN_USAGE.labels(
                operation=operation.value,
                model=model,
                token_type=token_type
            ).inc(count)


def record_error(
    operation: OperationType,
    model: str,
    error_type: str,
) -> None:
    """Record metrics for an OpenAI API error.
    
    Args:
        operation: Type of operation (completion, chat, embedding)
        model: Model used for the request
        error_type: Type of error that occurred
    """
    ERROR_COUNT.labels(
        operation=operation.value,
        model=model,
        error_type=error_type
    ).inc()


def record_retry(
    operation: OperationType,
    model: str,
) -> None:
    """Record metrics for an OpenAI API retry.
    
    Args:
        operation: Type of operation (completion, chat, embedding)
        model: Model used for the request
    """
    RETRY_COUNT.labels(operation=operation.value, model=model).inc()


def instrument_request(
    operation: OperationType,
) -> Callable[[F], F]:
    """Decorator to instrument OpenAI API requests with metrics.
    
    Args:
        operation: Type of operation (completion, chat, embedding)
        
    Returns:
        Decorator function that wraps an API call with metrics
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get model from kwargs
            model = kwargs.get("model", "unknown")
            
            # Increment current requests counter
            CURRENT_REQUESTS.labels(operation=operation.value, model=model).inc()
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                
                # Record successful request metrics
                duration = time.time() - start_time
                
                # Extract token usage if available
                tokens = None
                if hasattr(result, "usage"):
                    usage = result.usage
                    if usage:
                        tokens = {
                            "prompt": usage.prompt_tokens,
                            "completion": usage.completion_tokens or 0,
                            "total": usage.total_tokens
                        }
                
                record_request(
                    operation=operation,
                    model=model,
                    status="success",
                    duration=duration,
                    tokens=tokens
                )
                
                return result
            except Exception as e:
                # Record error metrics
                duration = time.time() - start_time
                error_type = type(e).__name__
                
                record_request(
                    operation=operation,
                    model=model,
                    status="error",
                    duration=duration
                )
                
                record_error(
                    operation=operation,
                    model=model,
                    error_type=error_type
                )
                
                raise
            finally:
                # Decrement current requests counter
                CURRENT_REQUESTS.labels(operation=operation.value, model=model).dec()
        
        return cast(F, wrapper)
    
    return decorator


def instrument_async_request(
    operation: OperationType,
) -> Callable[[F], F]:
    """Decorator to instrument async OpenAI API requests with metrics.
    
    Args:
        operation: Type of operation (completion, chat, embedding)
        
    Returns:
        Decorator function that wraps an async API call with metrics
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get model from kwargs
            model = kwargs.get("model", "unknown")
            
            # Increment current requests counter
            CURRENT_REQUESTS.labels(operation=operation.value, model=model).inc()
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                
                # Record successful request metrics
                duration = time.time() - start_time
                
                # Extract token usage if available
                tokens = None
                if hasattr(result, "usage"):
                    usage = result.usage
                    if usage:
                        tokens = {
                            "prompt": usage.prompt_tokens,
                            "completion": usage.completion_tokens or 0,
                            "total": usage.total_tokens
                        }
                
                record_request(
                    operation=operation,
                    model=model,
                    status="success",
                    duration=duration,
                    tokens=tokens
                )
                
                return result
            except Exception as e:
                # Record error metrics
                duration = time.time() - start_time
                error_type = type(e).__name__
                
                record_request(
                    operation=operation,
                    model=model,
                    status="error",
                    duration=duration
                )
                
                record_error(
                    operation=operation,
                    model=model,
                    error_type=error_type
                )
                
                raise
            finally:
                # Decrement current requests counter
                CURRENT_REQUESTS.labels(operation=operation.value, model=model).dec()
        
        return cast(F, wrapper)
    
    return decorator