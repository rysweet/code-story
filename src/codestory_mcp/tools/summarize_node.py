"""SummarizeNode tool implementation.

This module implements the summarizeNode tool for the MCP Adapter.
"""
from typing import Any
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
    name = 'summarizeNode'
    description = 'Generate a natural language summary of a code element'
    parameters = {'type': 'object', 'properties': {'node_id': {'type': 'string', 'description': 'ID of the node to summarize'}, 'include_context': {'type': 'boolean', 'description': 'Whether to include contextual information'}}, 'required': ['node_id']}

    def __init__(self: Any) -> None:
        """Initialize the tool."""
        self.graph_service = get_graph_service()
        self.openai_service = get_openai_service()
        self.metrics = get_metrics()

    async def __call__(self: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with the given parameters.

        Args:
            params: Tool parameters

        Returns:
            Tool execution results
        """
        node_id = params.get('node_id', '')
        include_context = params.get('include_context', True)
        if not node_id:
            raise ToolError('Node ID cannot be empty', status_code=status.HTTP_400_BAD_REQUEST)
        logger.info('Summarizing node', node_id=node_id, include_context=include_context)
        try:
            node = await self.graph_service.find_node(node_id)
            code = node.get('content', '')
            if not code:
                raise ToolError('Node does not contain code content to summarize', status_code=status.HTTP_400_BAD_REQUEST)
            context = None
            if include_context:
                node_name = node.get('name', '')
                node_type = node.labels[0] if node.labels else 'Unknown'
                node_path = node.get('path', '')
                context = f"{node_type} '{node_name}'"
                if node_path:
                    context += f' at {node_path}'
            summary = await self.openai_service.generate_code_summary(code=code, context=context, max_tokens=500)
            response = {'summary': summary, 'node': {'id': node_id, 'type': node.labels[0] if node.labels else 'Unknown', 'name': node.get('name', ''), 'path': node.get('path', '')}}
            response['metadata'] = {'node_id': node_id, 'include_context': include_context}
            logger.info('Node summarization completed', node_id=node_id, summary_length=len(summary))
            self.metrics.record_graph_operation('summarization')
            return response
        except Exception as e:
            logger.exception('Node summarization failed', node_id=node_id, error=str(e))
            if isinstance(e, ToolError):
                raise
            raise ToolError(f'Node summarization failed: {e!s}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e