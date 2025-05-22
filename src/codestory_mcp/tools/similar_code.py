"""SimilarCode tool implementation.

This module implements the similarCode tool for the MCP Adapter.
"""

from typing import Any

import structlog
from fastapi import status

from codestory_mcp.adapters.openai_service import get_openai_service
from codestory_mcp.tools import register_tool
from codestory_mcp.tools.base import BaseTool, ToolError
from codestory_mcp.utils.metrics import get_metrics

logger = structlog.get_logger(__name__)


@register_tool
class SimilarCodeTool(BaseTool):
    """Tool for finding semantically similar code to a given snippet."""

    name = "similarCode"
    description = "Find semantically similar code to a given snippet"

    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Code snippet to find similar code for",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return",
            },
        },
        "required": ["code"],
    }

    def __init__(self) -> None:
        """Initialize the tool."""
        self.openai_service = get_openai_service()
        self.metrics = get_metrics()

    async def __call__(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with the given parameters.

        Args:
            params: Tool parameters

        Returns:
            Tool execution results
        """
        # Extract parameters
        code = params.get("code", "")
        limit = params.get("limit", 5)

        # Validate parameters
        if not code:
            raise ToolError(
                "Code snippet cannot be empty", status_code=status.HTTP_400_BAD_REQUEST
            )

        if limit < 1:
            raise ToolError(
                "Limit must be a positive integer",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Log similarity search request
        logger.info("Finding similar code", code_length=len(code), limit=limit)

        try:
            # Find similar code
            results = await self.openai_service.find_similar_code(
                code=code, limit=limit
            )

            # Create response
            response = {"matches": results}

            # Add metadata to response
            response["metadata"] = {
                "code_length": len(code),
                "limit": limit,
                "result_count": len(results),
            }

            # Log success
            logger.info("Similar code search completed", result_count=len(results))

            return response

        except Exception as e:
            # Log error
            logger.exception("Similar code search failed", error=str(e))

            # Re-raise as tool error
            if isinstance(e, ToolError):
                raise

            raise ToolError(
                f"Similar code search failed: {e!s}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
