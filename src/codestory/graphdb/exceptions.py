"""Graph-specific exception classes for Neo4j operations."""

class Neo4jError(Exception):
    """Base exception for all Neo4j-related errors."""

class Neo4jConnectionError(Neo4jError):
    """Error establishing connection to Neo4j."""

class QueryError(Neo4jError):
    """Error executing a Cypher query."""

class SchemaError(Neo4jError):
    """Error with graph schema operation."""

class TransactionError(Neo4jError):
    """Error in transaction management."""
