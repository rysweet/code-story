"""SummarizeNode tool implementation.

This module implements the summarizeNode tool for the MCP Adapter.
"""

import time
from typing import Any, Dict, List, Optional

import structlog
from fastapi import status

from codestory_mcp.adapters.graph_service import get_graph_service
from codestory_mcp.adapters.openai_service import get_openai_service
from codestory_mcp.tools import register_tool
from codestory_mcp.tools.base import BaseTool, ToolError
from codestory_mcp.utils.metrics import get_metrics

logger = structlog.get_logger(__name__)


@register_tool
class SummarizeNodeTool(BaseTool):
    """Tool for generating a natural language summary of a code element."""

    name = "summarizeNode"
    description = "Generate a natural language summary of a code element"

    parameters = {
        "type": "object",
        "properties": {
            "node_id": {"type": "string", "description": "ID of the node to summarize"},
            "include_context": {
                "type": "boolean",
                "description": "Whether to include contextual information",
            },
        },
        "required": ["node_id"],
    }

    def __init__(self) -> None:
        """Initialize the tool."""
        self.graph_service = get_graph_service()
        self.openai_service = get_openai_service()
        self.metrics = get_metrics()

    async def __call__(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the given parameters.

        Args:
            params: Tool parameters

        Returns:
            Tool execution results
        """
        # Extract parameters
        node_id = params.get("node_id", "")
        include_context = params.get("include_context", True)

        # Validate parameters
        if not node_id:
            raise ToolError(
                "Node ID cannot be empty", status_code=status.HTTP_400_BAD_REQUEST
            )

        # Log summarization request
        logger.info(
            "Summarizing node", node_id=node_id, include_context=include_context
        )

        try:
            # Get node details
            node = await self.graph_service.find_node(node_id)

            # Extract code content
            code = node.get("content", "")

            if not code:
                raise ToolError(
                    "Node does not contain code content to summarize",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Get contextual information if requested
            context = None
            if include_context:
                # Get the node's name and type
                node_name = node.get("name", "")
                node_type = node.labels[0] if node.labels else "Unknown"
                node_path = node.get("path", "")

                # Build context string
                context = f"{node_type} '{node_name}'"
                if node_path:
                    context += f" at {node_path}"

            # Generate summary
            summary = await self.openai_service.generate_code_summary(
                code=code,
                context=context,
                max_tokens=500,  # Adjust based on typical summary length
            )

            # Create response
            response = {
                "summary": summary,
                "node": {
                    "id": node_id,
                    "type": node.labels[0] if node.labels else "Unknown",
                    "name": node.get("name", ""),
                    "path": node.get("path", ""),
                },
            }

            # Add metadata to response
            response["metadata"] = {
                "node_id": node_id,
                "include_context": include_context,
            }

            # Log success
            logger.info(
                "Node summarization completed",
                node_id=node_id,
                summary_length=len(summary),
            )

            # Record graph operation
            self.metrics.record_graph_operation("summarization")

            return response

        except Exception as e:
            # Log error
            logger.exception("Node summarization failed", node_id=node_id, error=str(e))

            # Re-raise as tool error
            if isinstance(e, ToolError):
                raise

            raise ToolError(
                f"Node summarization failed: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
