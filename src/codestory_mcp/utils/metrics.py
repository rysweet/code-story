"""Prometheus metrics collection for the MCP Adapter.

This module provides metrics collection for the MCP Adapter using Prometheus.
"""

from functools import lru_cache
from typing import Dict, List, Optional

from prometheus_client import Counter, Gauge, Histogram


class MCPMetrics:
    """Metrics collection for the MCP Adapter.

    This class provides metrics collection for the MCP Adapter using Prometheus.
    """

    def __init__(self) -> None:
        """Initialize metrics collectors."""
        # Tool call metrics
        self.tool_calls_total = Counter(
            "mcp_tool_calls_total",
            "Total number of tool calls",
            ["tool_name", "status"],
        )

        self.tool_call_duration = Histogram(
            "mcp_tool_call_duration_seconds",
            "Duration of tool calls in seconds",
            ["tool_name"],
            buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
                float("inf"),
            ),
        )

        # Authentication metrics
        self.auth_attempts_total = Counter(
            "mcp_auth_attempts_total",
            "Total number of authentication attempts",
            ["status"],
        )

        # Connection metrics
        self.active_connections = Gauge(
            "mcp_active_connections",
            "Number of active connections",
            ["protocol"],  # "http" or "grpc"
        )

        # Service metrics
        self.service_api_calls_total = Counter(
            "mcp_service_api_calls_total",
            "Total number of calls to the Code Story service API",
            ["endpoint", "status"],
        )

        self.service_api_call_duration = Histogram(
            "mcp_service_api_call_duration_seconds",
            "Duration of calls to the Code Story service API in seconds",
            ["endpoint"],
            buckets=(
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
                float("inf"),
            ),
        )

        # Graph operation metrics
        self.graph_operation_total = Counter(
            "mcp_graph_operation_total",
            "Total number of graph operations",
            ["operation_type"],  # search, path_finding, summarization
        )

    def record_tool_call(self, tool_name: str, status: str, duration: float) -> None:
        """Record a tool call.

        Args:
            tool_name: Name of the tool
            status: Status of the call (success, error)
            duration: Duration of the call in seconds
        """
        self.tool_calls_total.labels(tool_name=tool_name, status=status).inc()
        self.tool_call_duration.labels(tool_name=tool_name).observe(duration)

    def record_auth_attempt(self, status: str) -> None:
        """Record an authentication attempt.

        Args:
            status: Status of the attempt (success, error)
        """
        self.auth_attempts_total.labels(status=status).inc()

    def record_connection(self, protocol: str, count: int = 1) -> None:
        """Record a connection.

        Args:
            protocol: Connection protocol (http, grpc)
            count: Number of connections to add (or remove if negative)
        """
        self.active_connections.labels(protocol=protocol).inc(count)

    def record_service_api_call(
        self, endpoint: str, status: str, duration: float
    ) -> None:
        """Record a call to the Code Story service API.

        Args:
            endpoint: API endpoint
            status: Status of the call (success, error)
            duration: Duration of the call in seconds
        """
        self.service_api_calls_total.labels(endpoint=endpoint, status=status).inc()
        self.service_api_call_duration.labels(endpoint=endpoint).observe(duration)

    def record_graph_operation(self, operation_type: str) -> None:
        """Record a graph operation.

        Args:
            operation_type: Type of operation (search, path_finding, summarization)
        """
        self.graph_operation_total.labels(operation_type=operation_type).inc()


@lru_cache()
def get_metrics() -> MCPMetrics:
    """Get metrics singleton.

    Returns:
        Metrics instance
    """
    return MCPMetrics()
