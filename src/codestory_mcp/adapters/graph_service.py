"""Adapter for the Code Story Graph Service.

This module provides an adapter for interacting with the Code Story Graph Service.
"""

import time
from functools import lru_cache
from typing import Any

import httpx
import structlog
from fastapi import status
from neo4j.graph import Node, Relationship

from codestory_mcp.tools.base import ToolError
from codestory_mcp.utils.config import get_mcp_settings
from codestory_mcp.utils.metrics import get_metrics

logger = structlog.get_logger(__name__)


class GraphServiceAdapter:
    """Adapter for the Code Story Graph Service."""

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize the adapter.

        Args:
            base_url: Base URL of the Code Story service
        """
        settings = get_mcp_settings()
        self.base_url = base_url or settings.code_story_service_url
        self.metrics = get_metrics()

        # Create HTTP client for API requests
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            follow_redirects=True,
        )

    async def search(
        self, query: str, node_types: list[str] | None = None, limit: int = 10
    ) -> list[tuple[Node, float]]:
        """Search for nodes in the graph database.

        Args:
            query: Search query
            node_types: Optional list of node types to filter by
            limit: Maximum number of results to return

        Returns:
            List of nodes with relevance scores

        Raises:
            ToolError: If the search fails
        """
        start_time = time.time()
        endpoint = "/v1/query/search"

        try:
            # Prepare request payload
            payload = {
                "query": query,
                "limit": limit,
            }

            if node_types:
                payload["node_types"] = node_types

            # Make request to Code Story service
            response = await self.client.post(endpoint, json=payload)

            # Check for errors
            if response.status_code != 200:
                error_message = f"Search failed: {response.text}"
                logger.error(
                    "Search failed",
                    status_code=response.status_code,
                    error=response.text,
                )
                self.metrics.record_service_api_call(
                    endpoint, "error", time.time() - start_time
                )
                raise ToolError(error_message, status_code=status.HTTP_502_BAD_GATEWAY)

            # Record successful API call
            self.metrics.record_service_api_call(
                endpoint, "success", time.time() - start_time
            )

            # Extract results
            data = response.json()

            # Convert to Node objects with scores
            results = []
            for item in data.get("data", []):
                # Create Node-like object
                node = MockNode(
                    id=item.get("id"),
                    labels=[item.get("type")],
                    properties=item.get("properties", {}),
                )

                # Add result to list
                results.append((node, item.get("score", 1.0)))

            # Record graph operation
            self.metrics.record_graph_operation("search")

            return results

        except httpx.RequestError as e:
            # Handle network errors
            error_message = f"Search failed: {e!s}"
            logger.exception(
                "Search request error",
                error=str(e),
            )
            self.metrics.record_service_api_call(
                endpoint, "error", time.time() - start_time
            )
            raise ToolError(error_message, status_code=status.HTTP_502_BAD_GATEWAY) from e

    async def find_node(self, node_id: str) -> Node:
        """Find a node by ID.

        Args:
            node_id: ID of the node to find

        Returns:
            Node

        Raises:
            ToolError: If the node is not found
        """
        start_time = time.time()
        endpoint = f"/v1/query/node/{node_id}"

        try:
            # Make request to Code Story service
            response = await self.client.get(endpoint)

            # Check for errors
            if response.status_code != 200:
                error_message = "Node not found"
                if response.status_code != 404:
                    error_message = f"Failed to find node: {response.text}"

                logger.error(
                    "Node not found",
                    node_id=node_id,
                    status_code=response.status_code,
                    error=response.text,
                )
                self.metrics.record_service_api_call(
                    endpoint, "error", time.time() - start_time
                )
                raise ToolError(
                    error_message,
                    status_code=status.HTTP_404_NOT_FOUND
                    if response.status_code == 404
                    else status.HTTP_502_BAD_GATEWAY,
                )

            # Record successful API call
            self.metrics.record_service_api_call(
                endpoint, "success", time.time() - start_time
            )

            # Extract results
            data = response.json().get("data", {})

            # Create Node-like object
            node = MockNode(
                id=data.get("id"),
                labels=[data.get("type")],
                properties=data.get("properties", {}),
            )

            return node

        except httpx.RequestError as e:
            # Handle network errors
            error_message = f"Failed to find node: {e!s}"
            logger.exception(
                "Node request error",
                node_id=node_id,
                error=str(e),
            )
            self.metrics.record_service_api_call(
                endpoint, "error", time.time() - start_time
            )
            raise ToolError(error_message, status_code=status.HTTP_502_BAD_GATEWAY) from e

    async def find_paths(
        self, from_id: str, to_id: str, max_paths: int = 3
    ) -> list[list[Node | Relationship]]:
        """Find paths between two nodes.

        Args:
            from_id: ID of the source node
            to_id: ID of the target node
            max_paths: Maximum number of paths to return

        Returns:
            List of paths (each path is a list of alternating nodes and relationships)

        Raises:
            ToolError: If path finding fails
        """
        start_time = time.time()
        endpoint = "/v1/query/paths"

        try:
            # Prepare request payload
            payload = {
                "from_id": from_id,
                "to_id": to_id,
                "max_paths": max_paths,
            }

            # Make request to Code Story service
            response = await self.client.post(endpoint, json=payload)

            # Check for errors
            if response.status_code != 200:
                error_message = f"Path finding failed: {response.text}"
                logger.error(
                    "Path finding failed",
                    status_code=response.status_code,
                    error=response.text,
                )
                self.metrics.record_service_api_call(
                    endpoint, "error", time.time() - start_time
                )
                raise ToolError(error_message, status_code=status.HTTP_502_BAD_GATEWAY)

            # Record successful API call
            self.metrics.record_service_api_call(
                endpoint, "success", time.time() - start_time
            )

            # Extract results
            data = response.json()

            # Convert to paths of nodes and relationships
            paths = []
            for path_data in data.get("data", []):
                path = []

                # Process elements in the path
                for element in path_data.get("elements", []):
                    if element.get("element_type") == "node":
                        # Create Node-like object
                        node = MockNode(
                            id=element.get("id"),
                            labels=[element.get("type")],
                            properties=element.get("properties", {}),
                        )
                        path.append(node)
                    else:  # Relationship
                        # Create Relationship-like object
                        rel = MockRelationship(
                            id=element.get("id"),
                            type=element.get("type"),
                            start_node_id=element.get("start_node_id"),
                            end_node_id=element.get("end_node_id"),
                            properties=element.get("properties", {}),
                        )
                        path.append(rel)

                paths.append(path)

            # Record graph operation
            self.metrics.record_graph_operation("path_finding")

            return paths

        except httpx.RequestError as e:
            # Handle network errors
            error_message = f"Path finding failed: {e!s}"
            logger.exception(
                "Path finding request error",
                error=str(e),
            )
            self.metrics.record_service_api_call(
                endpoint, "error", time.time() - start_time
            )
            raise ToolError(error_message, status_code=status.HTTP_502_BAD_GATEWAY) from e

    async def execute_cypher(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a Cypher query.

        Args:
            query: Cypher query
            parameters: Optional query parameters

        Returns:
            Query results

        Raises:
            ToolError: If query execution fails
        """
        start_time = time.time()
        endpoint = "/v1/query/cypher"

        try:
            # Prepare request payload
            payload = {
                "query": query,
            }

            if parameters:
                payload["parameters"] = parameters

            # Make request to Code Story service
            response = await self.client.post(endpoint, json=payload)

            # Check for errors
            if response.status_code != 200:
                error_message = f"Cypher query failed: {response.text}"
                logger.error(
                    "Cypher query failed",
                    status_code=response.status_code,
                    error=response.text,
                )
                self.metrics.record_service_api_call(
                    endpoint, "error", time.time() - start_time
                )
                raise ToolError(error_message, status_code=status.HTTP_502_BAD_GATEWAY)

            # Record successful API call
            self.metrics.record_service_api_call(
                endpoint, "success", time.time() - start_time
            )

            # Return results
            return response.json()

        except httpx.RequestError as e:
            # Handle network errors
            error_message = f"Cypher query failed: {e!s}"
            logger.exception(
                "Cypher query request error",
                error=str(e),
            )
            self.metrics.record_service_api_call(
                endpoint, "error", time.time() - start_time
            )
            raise ToolError(error_message, status_code=status.HTTP_502_BAD_GATEWAY) from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class MockNode:
    """Mock Neo4j Node for use with the adapter."""

    def __init__(self, id: str, labels: list[str], properties: dict[str, Any]) -> None:
        """Initialize the mock node.

        Args:
            id: Node ID
            labels: Node labels
            properties: Node properties
        """
        self.id = id
        self.labels = labels
        self.properties = properties

    def get(self, key: str, default: Any = None) -> Any:
        """Get a property value.

        Args:
            key: Property key
            default: Default value if key is not found

        Returns:
            Property value or default
        """
        return self.properties.get(key, default)

    def items(self) -> list[tuple[str, Any]]:
        """Get all properties as key-value pairs.

        Returns:
            List of key-value pairs
        """
        return list(self.properties.items())

    def __getitem__(self, key: str) -> Any:
        """Get a property value.

        Args:
            key: Property key

        Returns:
            Property value

        Raises:
            KeyError: If key is not found
        """
        if key in self.properties:
            return self.properties[key]
        raise KeyError(key)


class MockRelationship:
    """Mock Neo4j Relationship for use with the adapter."""

    def __init__(
        self,
        id: str,
        type: str,
        start_node_id: str,
        end_node_id: str,
        properties: dict[str, Any],
    ) -> None:
        """Initialize the mock relationship.

        Args:
            id: Relationship ID
            type: Relationship type
            start_node_id: ID of the start node
            end_node_id: ID of the end node
            properties: Relationship properties
        """
        self.id = id
        self.type = type
        self.properties = properties

        # Create mock nodes
        self.start_node = MockNode(start_node_id, [], {})
        self.end_node = MockNode(end_node_id, [], {})

    def get(self, key: str, default: Any = None) -> Any:
        """Get a property value.

        Args:
            key: Property key
            default: Default value if key is not found

        Returns:
            Property value or default
        """
        return self.properties.get(key, default)

    def items(self) -> list[tuple[str, Any]]:
        """Get all properties as key-value pairs.

        Returns:
            List of key-value pairs
        """
        return list(self.properties.items())

    def __getitem__(self, key: str) -> Any:
        """Get a property value.

        Args:
            key: Property key

        Returns:
            Property value

        Raises:
            KeyError: If key is not found
        """
        if key in self.properties:
            return self.properties[key]
        raise KeyError(key)


@lru_cache
def get_graph_service() -> GraphServiceAdapter:
    """Get the graph service adapter singleton.

    Returns:
        Graph service adapter
    """
    return GraphServiceAdapter()
