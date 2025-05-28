"""Prometheus metrics for Neo4j operations.

This module provides metrics for Neo4j database operations, including:
- Query execution times
- Connection pool utilization
- Error rates
- Query counts by type

Metrics are exposed through the Prometheus client library.
"""

import time
from collections.abc import Callable
from enum import Enum
from typing import Any, Callable, Callable, Callable, Callable, TypeVar, cast

# Use lazy import for prometheus_client to avoid hard dependency
try:
    from prometheus_client import Counter, Gauge, Histogram, Summary

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Define type for decorated functions
F = TypeVar("F", bound=Callable[..., Any])

# Define metric prefix
METRIC_PREFIX = "codestory_neo4j"


class QueryType(str, Enum):
    """Types of database queries."""

    READ = "read"
    WRITE = "write"
    SCHEMA = "schema"


# Initialize metrics if prometheus_client is available
if PROMETHEUS_AVAILABLE:
    # Use a custom registry to avoid conflicts with the default registry
    from prometheus_client import REGISTRY

    # Create metrics only once - check if they already exist
    # and only define them if they don't
    try:
        # Try to get the metric from the registry
        QUERY_DURATION = REGISTRY.get_sample_value(f"{METRIC_PREFIX}_query_duration_seconds_count")
        # If we get here, the metric exists, so reuse it instead of creating a new one
        from prometheus_client import metrics

        for metric in metrics.REGISTRY._names_to_collectors.values():
            if metric.name == f"{METRIC_PREFIX}_query_duration_seconds":  # type: ignore[attr-defined]
                QUERY_DURATION = metric  # type: ignore  # TODO: Fix type compatibility
                break
    except Exception:
        # If we get an exception, the metric doesn't exist, so create it
        try:
            QUERY_DURATION = Histogram(  # type: ignore  # TODO: Fix type compatibility
                name=f"{METRIC_PREFIX}_query_duration_seconds",
                documentation="Duration of Neo4j query execution in seconds",
                labelnames=["query_type"],
                buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            )
        except ValueError:
            # If there's a value error, the metric already exists somewhere
            # Use a dummy version that can be called without affecting metrics
            class DummyHistogram:
                """Dummy histogram class for when Prometheus is not available."""
                
                def observe(self, value, **kwargs) -> Any:  # type: ignore[no-untyped-def]
                    """Dummy observe method that does nothing."""
                    pass

                def time(self) -> Any:
                    """Dummy timer method that returns a dummy timer context."""
                    class DummyTimer:
                        def __enter__(self) -> None:
                            return self  # type: ignore[return-value]

                        def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
                            pass

                    return DummyTimer()

            QUERY_DURATION = DummyHistogram()  # type: ignore  # TODO: Fix type compatibility

    QUERY_COUNT = Counter(
        name=f"{METRIC_PREFIX}_query_count_total",
        documentation="Total number of Neo4j queries executed",
        labelnames=["query_type", "status"],
    )

    # Connection pool metrics
    POOL_SIZE = Gauge(
        name=f"{METRIC_PREFIX}_connection_pool_size",
        documentation="Current size of the Neo4j connection pool",
    )

    POOL_ACQUIRED = Gauge(
        name=f"{METRIC_PREFIX}_connection_pool_acquired",
        documentation="Number of connections currently acquired from the pool",
    )

    # Retry metrics
    RETRY_COUNT = Counter(
        name=f"{METRIC_PREFIX}_retry_count_total",
        documentation="Total number of Neo4j query retries",
        labelnames=["query_type"],
    )

    # Connection metrics
    CONNECTION_ERRORS = Counter(
        name=f"{METRIC_PREFIX}_connection_errors_total",
        documentation="Total number of Neo4j connection errors",
    )

    # Transaction metrics
    TRANSACTION_COUNT = Counter(
        name=f"{METRIC_PREFIX}_transaction_count_total",
        documentation="Total number of Neo4j transactions",
        labelnames=["status"],
    )

    # Vector search metrics
    try:
        # Try to get the metric from the registry
        VECTOR_SEARCH_DURATION = REGISTRY.get_sample_value(
            f"{METRIC_PREFIX}_vector_search_duration_seconds_count"
        )
        # If we get here, the metric exists, so reuse it instead of creating a new one
        for metric in metrics.REGISTRY._names_to_collectors.values():
            if metric.name == f"{METRIC_PREFIX}_vector_search_duration_seconds":  # type: ignore[attr-defined]
                VECTOR_SEARCH_DURATION = metric  # type: ignore  # TODO: Fix type compatibility
                break
    except Exception:
        # If we get an exception, the metric doesn't exist, so create it
        try:
            VECTOR_SEARCH_DURATION = Histogram(  # type: ignore  # TODO: Fix type compatibility
                name=f"{METRIC_PREFIX}_vector_search_duration_seconds",
                documentation="Duration of Neo4j vector similarity search in seconds",
                labelnames=["node_label"],
                buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            )
        except ValueError:
            # If there's a value error, the metric already exists somewhere
            # Use a dummy version that can be called without affecting metrics
            VECTOR_SEARCH_DURATION = DummyHistogram()  # type: ignore  # TODO: Fix type compatibility


def instrument_query(
    query_type: QueryType = QueryType.READ,
) -> Callable[[F], F]:
    """Decorator to instrument Neo4j query execution with metrics.

    Args:
        query_type: Type of query (read, write, schema)

    Returns:
        Decorated function that records metrics
    """

    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not PROMETHEUS_AVAILABLE:
                return func(*args, **kwargs)

            # Record metrics
            start_time = time.time()
            success = False

            try:
                result = func(*args, **kwargs)
                success = True
                return result
            finally:
                duration = time.time() - start_time

                # Record query duration
                QUERY_DURATION.labels(query_type=query_type.value).observe(duration)  # type: ignore[union-attr]

                # Record query count
                status = "success" if success else "error"
                QUERY_COUNT.labels(query_type=query_type.value, status=status).inc()

        return cast("F", wrapper)

    return decorator


def record_retry(query_type: QueryType) -> None:
    """Record a query retry in metrics.

    Args:
        query_type: Type of query being retried
    """
    if PROMETHEUS_AVAILABLE:
        RETRY_COUNT.labels(query_type=query_type.value).inc()


def record_connection_error() -> None:
    """Record a connection error in metrics."""
    if PROMETHEUS_AVAILABLE:
        CONNECTION_ERRORS.inc()


def record_transaction(success: bool) -> None:
    """Record a transaction in metrics.

    Args:
        success: Whether the transaction was successful
    """
    if PROMETHEUS_AVAILABLE:
        status = "committed" if success else "rolled_back"
        TRANSACTION_COUNT.labels(status=status).inc()


def update_pool_metrics(pool_size: int, acquired: int) -> None:
    """Update connection pool metrics.

    Args:
        pool_size: Current size of the connection pool
        acquired: Number of connections currently acquired
    """
    if PROMETHEUS_AVAILABLE:
        POOL_SIZE.set(pool_size)
        POOL_ACQUIRED.set(acquired)


def record_vector_search(node_label: str, duration: float) -> None:
    """Record a vector similarity search in metrics.

    Args:
        node_label: Label of nodes being searched
        duration: Duration of the search in seconds
    """
    if PROMETHEUS_AVAILABLE:
        VECTOR_SEARCH_DURATION.labels(node_label=node_label).observe(duration)  # type: ignore[union-attr]
