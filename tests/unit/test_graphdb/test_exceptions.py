"""Tests for graph database exceptions."""

import pytest

from codestory.graphdb.exceptions import (
    Neo4jError,
    ConnectionError,
    QueryError,
    SchemaError,
    TransactionError,
)


def test_neo4j_error():
    """Test Neo4jError base class."""
    # Create with minimal args
    error = Neo4jError("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.details == {}

    # Create with details
    details = {"test": "value"}
    error = Neo4jError("Test error", details)
    assert error.message == "Test error"
    assert error.details == details


def test_connection_error():
    """Test ConnectionError class."""
    # Create with minimal args
    error = ConnectionError("Connection failed")
    assert str(error) == "Connection failed"
    assert error.message == "Connection failed"
    assert error.details["uri"] is None
    assert error.details["cause"] is None
    assert error.cause is None

    # Create with all args
    cause = ValueError("Invalid URI")
    error = ConnectionError(
        "Connection failed",
        uri="bolt://localhost:7687",
        cause=cause,
        timeout=30,
    )
    assert error.message == "Connection failed"
    assert error.details["uri"] == "bolt://localhost:7687"
    assert error.details["cause"] == str(cause)
    assert error.details["timeout"] == 30
    assert error.cause is cause


def test_query_error():
    """Test QueryError class."""
    # Create with minimal args
    error = QueryError("Query failed")
    assert str(error) == "Query failed"
    assert error.message == "Query failed"
    assert error.details["query"] is None
    assert error.details["parameters"] is None
    assert error.details["cause"] is None
    assert error.cause is None

    # Create with sensitive parameters
    error = QueryError(
        "Query failed",
        query="MATCH (n) RETURN n",
        parameters={"password": "secret", "key": "value", "normal": "data"},
    )
    assert error.details["query"] == "MATCH (n) RETURN n"
    assert error.details["parameters"]["password"] == "********"
    assert error.details["parameters"]["key"] == "********"
    assert error.details["parameters"]["normal"] == "data"

    # Create with other details
    cause = ValueError("Syntax error")
    error = QueryError(
        "Query failed",
        query="MATCH (n) RETURN n",
        parameters={"name": "test"},
        cause=cause,
        attempt=3,
    )
    assert error.details["cause"] == str(cause)
    assert error.details["attempt"] == 3
    assert error.cause is cause


def test_schema_error():
    """Test SchemaError class."""
    # Create with minimal args
    error = SchemaError("Schema operation failed")
    assert str(error) == "Schema operation failed"
    assert error.message == "Schema operation failed"
    assert error.details["operation"] is None
    assert error.details["cause"] is None
    assert error.cause is None

    # Create with all args
    cause = ValueError("Invalid constraint")
    error = SchemaError(
        "Schema operation failed",
        operation="create_constraint",
        cause=cause,
        constraint_name="unique_node",
    )
    assert error.details["operation"] == "create_constraint"
    assert error.details["cause"] == str(cause)
    assert error.details["constraint_name"] == "unique_node"
    assert error.cause is cause


def test_transaction_error():
    """Test TransactionError class."""
    # Create with minimal args
    error = TransactionError("Transaction failed")
    assert str(error) == "Transaction failed"
    assert error.message == "Transaction failed"
    assert error.details["operation"] is None
    assert error.details["cause"] is None
    assert error.cause is None

    # Create with all args
    cause = ValueError("Transaction timeout")
    error = TransactionError(
        "Transaction failed",
        operation="execute_many",
        cause=cause,
        query_count=5,
    )
    assert error.details["operation"] == "execute_many"
    assert error.details["cause"] == str(cause)
    assert error.details["query_count"] == 5
    assert error.cause is cause
