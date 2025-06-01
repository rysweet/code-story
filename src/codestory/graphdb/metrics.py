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
from contextlib import contextmanager
from enum import Enum
from typing import Any, Iterator, Protocol, TypeVar, Union, cast

try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
F = TypeVar("F", bound=Callable[..., Any])
METRIC_PREFIX = "codestory_neo4j"


class QueryType(str, Enum):
    """Types of database queries."""

    READ = "read"
    WRITE = "write"
    SCHEMA = "schema"


class HistogramLike(Protocol):
    """Protocol for histogram-like objects."""

    def observe(self: Any, amount: float, exemplar: Any = None) -> None:
        """Record an observation."""
        ...

    def labels(self: Any, *labelvalues: Any, **labelkwargs: Any) -> "HistogramLike":
        """Get labeled instance."""
        ...


class DummyHistogram:
    """Dummy histogram class for when Prometheus is not available."""

    def observe(self: Any, amount: float, exemplar: Any = None) -> None:
        """Dummy observe method that does nothing."""
        pass

    def labels(
        self: "DummyHistogram", *labelvalues: Any, **labelkwargs: Any
    ) -> "DummyHistogram":
        """Return self for method chaining."""
        return self

    def inc(self: Any, amount: float = 1.0) -> None:
        """Dummy inc method that does nothing."""
        pass

    def set(self: Any, value: float) -> None:
        """Dummy set method that does nothing."""
        pass

    @contextmanager
    def time(self: Any) -> "Iterator[None]":
        """Dummy timer method that returns a dummy timer context."""
        yield


class CounterLike(Protocol):
    """Protocol for counter-like objects."""

    def inc(self: Any, amount: float = 1.0) -> None:
        """Increment counter."""
        ...

    def labels(self: Any, **kwargs: Any) -> "CounterLike":
        """Get labeled instance."""
        ...


class GaugeLike(Protocol):
    """Protocol for gauge-like objects."""

    def set(self: Any, value: float) -> None:
        """Set gauge value."""
        ...


QUERY_DURATION: HistogramLike
QUERY_COUNT: CounterLike
POOL_SIZE: GaugeLike
POOL_ACQUIRED: GaugeLike
RETRY_COUNT: CounterLike
CONNECTION_ERRORS: CounterLike
TRANSACTION_COUNT: CounterLike
VECTOR_SEARCH_DURATION: HistogramLike
if PROMETHEUS_AVAILABLE:
    QUERY_DURATION = Histogram(
        name=f"{METRIC_PREFIX}_query_duration_seconds",
        documentation="Duration of Neo4j query execution in seconds",
        labelnames=["query_type"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    QUERY_COUNT = Counter(
        name=f"{METRIC_PREFIX}_query_count_total",
        documentation="Total number of Neo4j queries executed",
        labelnames=["query_type", "status"],
    )
    POOL_SIZE = Gauge(
        name=f"{METRIC_PREFIX}_connection_pool_size",
        documentation="Current size of the Neo4j connection pool",
    )
    POOL_ACQUIRED = Gauge(
        name=f"{METRIC_PREFIX}_connection_pool_acquired",
        documentation="Number of connections currently acquired from the pool",
    )
    RETRY_COUNT = Counter(
        name=f"{METRIC_PREFIX}_retry_count_total",
        documentation="Total number of Neo4j query retries",
        labelnames=["query_type"],
    )
    CONNECTION_ERRORS = Counter(
        name=f"{METRIC_PREFIX}_connection_errors_total",
        documentation="Total number of Neo4j connection errors",
    )
    TRANSACTION_COUNT = Counter(
        name=f"{METRIC_PREFIX}_transaction_count_total",
        documentation="Total number of Neo4j transactions",
        labelnames=["status"],
    )
    VECTOR_SEARCH_DURATION = Histogram(
        name=f"{METRIC_PREFIX}_vector_search_duration_seconds",
        documentation="Duration of Neo4j vector similarity search in seconds",
        labelnames=["node_label"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )
else:
    _dummy_histogram = DummyHistogram()
    _dummy_counter = cast("CounterLike", _dummy_histogram)
    _dummy_gauge = cast("GaugeLike", _dummy_histogram)
    QUERY_DURATION = _dummy_histogram
    QUERY_COUNT = _dummy_counter
    POOL_SIZE = _dummy_gauge
    POOL_ACQUIRED = _dummy_gauge
    RETRY_COUNT = _dummy_counter
    CONNECTION_ERRORS = _dummy_counter
    TRANSACTION_COUNT = _dummy_counter
    VECTOR_SEARCH_DURATION = _dummy_histogram


def instrument_query(query_type: QueryType = QueryType.READ) -> Callable[[F], F]:
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
            start_time = time.time()
            success = False
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            finally:
                duration = time.time() - start_time
                QUERY_DURATION.labels(query_type=query_type.value).observe(duration)
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
        POOL_SIZE.set(float(pool_size))
        POOL_ACQUIRED.set(float(acquired))


def record_vector_search(node_label: str, duration: float) -> None:
    """Record a vector similarity search in metrics.

    Args:
        node_label: Label of nodes being searched
        duration: Duration of the search in seconds
    """
    if PROMETHEUS_AVAILABLE:
        VECTOR_SEARCH_DURATION.labels(node_label=node_label).observe(duration)
