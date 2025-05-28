"""PathTo tool implementation.

This module implements the pathTo tool for the MCP Adapter.
"""

from typing import Any

import structlog
from fastapi import status

from codestory_mcp.adapters.graph_service import get_graph_service
from codestory_mcp.adapters.openai_service import get_openai_service
from codestory_mcp.tools import register_tool
from codestory_mcp.tools.base import BaseTool, ToolError
from codestory_mcp.utils.metrics import get_metrics
from codestory_mcp.utils.serializers import RelationshipSerializer

logger = structlog.get_logger(__name__)


@register_tool
class PathToTool(BaseTool):
    """Tool for finding paths between two code elements."""

    name = "pathTo"
    description = "Find paths between two code elements"

    parameters = {
        "type": "object",
        "properties": {
            "from_id": {"type": "string", "description": "ID of the source node"},
            "to_id": {"type": "string", "description": "ID of the target node"},
            "max_paths": {
                "type": "integer",
                "description": "Maximum number of paths to return",
            },
            "include_explanation": {
                "type": "boolean",
                "description": "Whether to include a natural language explanation of the path",
            },
        },
        "required": ["from_id", "to_id"],
    }

    def __init__(self) -> None:
        """Initialize the tool."""
        self.graph_service = get_graph_service()
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
        from_id = params.get("from_id", "")
        to_id = params.get("to_id", "")
        max_paths = params.get("max_paths", 3)
        include_explanation = params.get("include_explanation", True)

        # Validate parameters
        if not from_id:
            raise ToolError(
                "Source node ID cannot be empty",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not to_id:
            raise ToolError(
                "Target node ID cannot be empty",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if max_paths < 1:
            raise ToolError(
                "Maximum paths must be a positive integer",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Log path finding request
        logger.info(
            "Finding paths between nodes",
            from_id=from_id,
            to_id=to_id,
            max_paths=max_paths,
        )

        try:
            # Find paths
            paths = await self.graph_service.find_paths(
                from_id=from_id, to_id=to_id, max_paths=max_paths
            )

            # Transform paths to MCP format
            response = RelationshipSerializer.to_mcp_path_result(
                paths=paths,
                # Exclude potentially large content field from nodes
                exclude_node_properties=["content"],
            )

            # Add explanation if requested
            if include_explanation and paths:
                # Use the first path for explanation
                first_path = paths[0]

                # Extract elements for explanation
                path_elements: list[Any] = []
                for i, element in enumerate(first_path):
                    if i % 2 == 0:  # Node
                        path_elements.append(
                            {
                                "element_type": "node",
                                "id": str(element.id),
                                "type": element.labels[0] if element.labels else "Unknown",
                                "name": element.get("name", ""),
                                "content": element.get("content", "")[:200],  # Limit content size
                            }
                        )
                    else:  # Relationship
                        path_elements.append(
                            {
                                "element_type": "relationship",
                                "id": str(element.id),
                                "type": element.type,
                            }
                        )

                # Generate explanation
                explanation = await self.openai_service.generate_path_explanation(
                    path_elements=path_elements
                )

                # Add explanation to response
                response["explanation"] = explanation  # type: ignore  # TODO: Fix type compatibility

            # Add metadata to response
            response["metadata"] = {  # type: ignore  # TODO: Fix type compatibility
                "from_id": from_id,
                "to_id": to_id,
                "max_paths": max_paths,
                "path_count": len(paths),
            }

            # Log success
            logger.info(
                "Path finding completed",
                from_id=from_id,
                to_id=to_id,
                path_count=len(paths),
            )

            return response

        except Exception as e:
            # Log error
            logger.exception("Path finding failed", from_id=from_id, to_id=to_id, error=str(e))

            # Re-raise as tool error
            if isinstance(e, ToolError):
                raise

            raise ToolError(
                f"Path finding failed: {e!s}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from e