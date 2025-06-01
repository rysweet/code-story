"""SearchGraph tool implementation.

This module implements the searchGraph tool for the MCP Adapter.
"""
from typing import Any

import structlog
from fastapi import status

from codestory_mcp.adapters.graph_service import get_graph_service
from codestory_mcp.tools import register_tool
from codestory_mcp.tools.base import BaseTool, ToolError
from codestory_mcp.utils.metrics import get_metrics
from codestory_mcp.utils.serializers import NodeSerializer

logger = structlog.get_logger(__name__)


@register_tool
class SearchGraphTool(BaseTool):
    """Tool for searching the code graph using various criteria."""

    name = "searchGraph"
    description = (
        "Search for nodes in the code graph by name, type, or semantic similarity"
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term or natural language description",
            },
            "node_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional filter for specific node types (e.g., 'Class', 'Function')",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return",
            },
        },
        "required": ["query"],
    }

    def __init__(self: Any) -> None:
        """Initialize the tool."""
        self.graph_service = get_graph_service()
        self.metrics = get_metrics()

    async def __call__(self: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with the given parameters.

        Args:
            params: Tool parameters

        Returns:
            Tool execution results
        """
        query = params.get("query", "")
        node_types = params.get("node_types", [])
        limit = params.get("limit", 10)
        if not query:
            raise ToolError(
                "Search query cannot be empty", status_code=status.HTTP_400_BAD_REQUEST
            )
        if limit < 1:
            raise ToolError(
                "Limit must be a positive integer",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        logger.info("Searching graph", query=query, node_types=node_types, limit=limit)
        try:
            results = await self.graph_service.search(
                query=query, node_types=node_types, limit=limit
            )
            response = NodeSerializer.to_mcp_result(
                results, exclude_properties=["content"]
            )
            response["metadata"] = {"query": query, "node_types": node_types, "limit": limit, "result_count": len(response["matches"])}  # type: ignore[assignment]
            logger.info(
                "Search completed", query=query, result_count=len(response["matches"])
            )
            return response
        except Exception as e:
            logger.exception("Search failed", query=query, error=str(e))
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Search failed: {e!s}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from e
