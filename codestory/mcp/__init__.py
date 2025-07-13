from __future__ import annotations
from typing import Any, List

from codestory.graph import GraphService

class MCPAdapter:  # noqa: D101
    def __init__(self, graph_service: GraphService) -> None:
        self.graph_service = graph_service

    async def searchGraph(self, cypher: str, **params: Any) -> List[dict[str, Any]]:  # noqa: N802
        """
        Execute an arbitrary Cypher query and return list of dictionaries.
        """
        return await self.graph_service.execute(cypher, **params)

    async def summarizeNode(self, node_id: str) -> str:  # noqa: N802
        """
        Placeholder summary logic – to be replaced with real summarizer.
        """
        # For now, return a static stub; real implementation later.
        return f"Summary for node {node_id}"

    async def pathTo(self, src: str, dst: str) -> List[str]:  # noqa: N802
        """
        Placeholder path finding – returns stub path.
        """
        return [src, "…", dst]

    async def similarCode(self, node_id: str) -> List[str]:  # noqa: N802
        """
        Placeholder similar code search.
        """
        return []

__all__ = ["MCPAdapter"]