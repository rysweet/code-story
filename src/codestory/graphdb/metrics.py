"""Prometheus metrics for Neo4j operations."""
from prometheus_client import Counter, Gauge, Histogram

neo4j_query_counter = Counter(
    "neo4j_queries_total",
    "Total number of Neo4j queries executed",
    ["operation", "success"]
)

neo4j_query_duration = Histogram(
    "neo4j_query_duration_seconds",
    "Duration of Neo4j queries in seconds",
    ["operation"]
)

neo4j_connection_gauge = Gauge(
    "neo4j_active_connections",
    "Number of active Neo4j connections"
)
