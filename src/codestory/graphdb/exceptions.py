"""Graph database related exceptions.

This module defines custom exception classes for the graph database module.
"""

from typing import Any


class Neo4jError(Exception):
    """Base exception for all Neo4j-related errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Neo4jError.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ExportError(Neo4jError):
    """Error exporting data from Neo4j."""

    def __init__(
        self,
        message: str,
        format: str | None = None,
        path: str | None = None,
        cause: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ExportError.

        Args:
            message: Error message
            format: Export format (e.g., JSON, CSV)
            path: Export file path
            cause: Original exception that caused this error
            **kwargs: Additional details to include
        """
        details = {
            "format": format,
            "path": path,
            "cause": str(cause) if cause else None,
            **kwargs,
        }
        self.cause = cause
        super().__init__(message, details)


class ConnectionError(Neo4jError):
    """Error establishing connection to Neo4j."""

    def __init__(
        self, message: str, uri: str | None = None, cause: Exception | None = None, **kwargs: Any
    ) -> None:
        """Initialize ConnectionError.

        Args:
            message: Error message
            uri: Neo4j URI that failed to connect
            cause: Original exception that caused this error
            **kwargs: Additional details to include
        """
        details = {"uri": uri, "cause": str(cause) if cause else None, **kwargs}
        self.cause = cause
        super().__init__(message, details)


class QueryError(Neo4jError):
    """Error executing a Cypher query."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        parameters: dict[str, Any] | None = None,
        cause: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize QueryError.

        Args:
            message: Error message
            query: The Cypher query that failed
            parameters: Query parameters
            cause: Original exception that caused this error
            **kwargs: Additional details to include
        """
        # Redact sensitive parameters like passwords
        safe_params: dict[Any, Any] | None = None
        if parameters:
            safe_params = {}
            for k, v in parameters.items():
                if any(sensitive in k.lower() for sensitive in ["password", "secret", "key"]):
                    safe_params[k] = "********"  # Redact sensitive values
                else:
                    safe_params[k] = v

        details = {
            "query": query,
            "parameters": safe_params,
            "cause": str(cause) if cause else None,
            **kwargs,
        }
        self.cause = cause
        super().__init__(message, details)


class SchemaError(Neo4jError):
    """Error with graph schema operation."""

    def __init__(
        self, message: str, operation: str | None = None, cause: Exception | None = None, **kwargs: Any
    ) -> None:
        """Initialize SchemaError.

        Args:
            message: Error message
            operation: Schema operation that failed (e.g., creating constraint)
            cause: Original exception that caused this error
            **kwargs: Additional details to include
        """
        details = {
            "operation": operation,
            "cause": str(cause) if cause else None,
            **kwargs,
        }
        self.cause = cause
        super().__init__(message, details)


class TransactionError(Neo4jError):
    """Error in transaction management."""

    def __init__(
        self, message: str, operation: str | None = None, cause: Exception | None = None, **kwargs: Any
    ) -> None:
        """Initialize TransactionError.

        Args:
            message: Error message
            operation: Transaction operation that failed
            cause: Original exception that caused this error
            **kwargs: Additional details to include
        """
        details = {
            "operation": operation,
            "cause": str(cause) if cause else None,
            **kwargs,
        }
        self.cause = cause
        super().__init__(message, details)