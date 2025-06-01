"""Base tool implementation for MCP.

This module defines the base class for all MCP tools.
"""
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict


class ToolParameters(BaseModel):
    """Base model for tool parameters."""

    model_config = ConfigDict(extra="forbid")


class BaseTool(ABC):
    """Base class for all MCP tools.

    All tools must inherit from this class and implement the __call__ method.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[dict[str, Any]]

    @abstractmethod
    def __init__(self: Any) -> None:
        """Initialize the tool."""
        pass

    @abstractmethod
    async def __call__(self: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with the given parameters.

        Args:
            params: Tool parameters

        Returns:
            Tool execution results

        Raises:
            HTTPException: If the tool execution fails
        """
        pass

    def validate_parameters(self: Any, params: dict[str, Any]) -> None:
        """Validate tool parameters.

        Args:
            params: Parameters to validate

        Raises:
            HTTPException: If parameters are invalid
        """
        required_params = []
        if "properties" in self.parameters and "required" in self.parameters:
            required_params = self.parameters["required"]
        for param_name in required_params:
            if param_name not in params:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required parameter: {param_name}",
                )


class ToolError(Exception):
    """Error during tool execution."""

    def __init__(
        self: Any,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Optional error code
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)
