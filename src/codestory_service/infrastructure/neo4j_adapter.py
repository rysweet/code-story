"""Neo4j adapter for the Code Story Service.

This module provides a service-specific adapter for Neo4j operations,
building on the core Neo4jConnector with additional functionality required
by the service layer.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from fastapi import HTTPException, status

from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.graphdb.exceptions import (
    ConnectionError,
    Neo4jError,
    QueryError,
    SchemaError,
    TransactionError,
)

from ..domain.graph import (
    CypherQuery,
    QueryResult,
    QueryResultFormat,
    VectorQuery,
    VectorResult,
    SearchResult,
    PathRequest,
    PathResult,
    Path,
    PathNode,
    PathRelationship,
)

# Set up logging
logger = logging.getLogger(__name__)


class Neo4jAdapter:
    """Adapter for Neo4j operations specific to the service layer.

    This class wraps the core Neo4jConnector, providing methods that map
    directly to the service's use cases and handling conversion between
    domain models and Neo4j data structures.
    """

    def __init__(self, connector: Optional[Neo4jConnector] = None) -> None:
        """Initialize the Neo4j adapter.

        Args:
            connector: Optional existing Neo4jConnector instance.
                      If not provided, a new one will be created.

        Raises:
            ConnectionError: If connection to Neo4j fails
        """
        self.connector = connector or Neo4jConnector()

    async def check_health(self) -> Dict[str, Any]:
        """Check Neo4j database health.

        Returns:
            Dictionary containing health information

        Raises:
            HTTPException: If the health check fails
        """
        try:
            # Use an executor to run the synchronous method in a thread pool
            # to avoid blocking the async event loop
            import asyncio
            loop = asyncio.get_event_loop()
            connection_info = await loop.run_in_executor(
                None, self.connector.check_connection
            )

            return {
                "status": "healthy",
                "details": {
                    "database": connection_info.get("database", "unknown"),
                    "components": connection_info.get("components", []),
                },
            }
        except Exception as e:
            logger.error(f"Neo4j health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "details": {
                    "error": str(e),
                    "type": type(e).__name__,
                },
            }

    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self.connector:
            # Use synchronous method since async one is not available
            self.connector.close()

    async def execute_cypher_query(self, query_model: CypherQuery) -> QueryResult:
        """Execute a Cypher query with the given parameters.

        Args:
            query_model: CypherQuery domain model

        Returns:
            QueryResult with the query results

        Raises:
            HTTPException: If the query execution fails
        """
        start_time = time.time()

        try:
            # Use synchronous method since async one is not available
            result = self.connector.execute_query(
                query_model.query,
                params=query_model.parameters,
                write=query_model.query_type.value == "write",
            )

            # Extract column names from the first record if available
            columns = []
            if result and len(result) > 0:
                columns = list(result[0].keys())

            # Extract rows as lists to match the domain model
            rows = []
            for record in result:
                row = [record.get(col) for col in columns]
                rows.append(row)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=execution_time_ms,
                has_more=False,  # We don't support pagination in direct Cypher queries
                format=QueryResultFormat.TABULAR,
            )

        except (QueryError, TransactionError) as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query execution failed: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error in query execution: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            )

    async def execute_vector_search(
        self, query_model: VectorQuery, embedding: List[float]
    ) -> VectorResult:
        """Execute a vector similarity search.

        Args:
            query_model: VectorQuery domain model
            embedding: Pre-computed vector embedding for the search

        Returns:
            VectorResult with the search results

        Raises:
            HTTPException: If the search fails
        """
        start_time = time.time()
        embedding_time = 0  # This would be set if we computed the embedding here

        try:
            # Determine node label based on entity type
            node_label = "*"  # Default for any entity type
            if query_model.entity_type and query_model.entity_type.value != "any":
                # Map domain entity type to Neo4j label
                entity_type_map = {
                    "node": "*",
                    "file": "File",
                    "function": "Function",
                    "class": "Class",
                    "module": "Module",
                    "directory": "Directory",
                    "document": "Document",
                }
                node_label = entity_type_map.get(query_model.entity_type.value, "*")

            # Execute vector search query with synchronous method
            result = self.connector.execute_query(
                f"""
                MATCH (n{':' + node_label if node_label != '*' else ''})
                WHERE n.embedding IS NOT NULL
                WITH n, gds.similarity.cosine(n.embedding, $embedding) AS score
                WHERE score >= $min_score
                RETURN n, score
                ORDER BY score DESC
                LIMIT $limit
                """,
                params={
                    "embedding": embedding,
                    "min_score": query_model.min_score,
                    "limit": query_model.limit,
                },
            )

            # Map results to domain model
            search_results = []
            for item in result:
                node = item.get("n", {})

                # Extract path for file-based entities
                path = None
                if "path" in node:
                    path = node["path"]
                elif "filePath" in node:
                    path = node["filePath"]

                # Determine entity type
                entity_type = "unknown"
                if "labels" in node and isinstance(node["labels"], list):
                    if "File" in node["labels"]:
                        entity_type = "file"
                    elif "Function" in node["labels"]:
                        entity_type = "function"
                    elif "Class" in node["labels"]:
                        entity_type = "class"
                    elif "Module" in node["labels"]:
                        entity_type = "module"
                    elif "Directory" in node["labels"]:
                        entity_type = "directory"
                    elif "Document" in node["labels"]:
                        entity_type = "document"

                # Extract content snippet if available
                content_snippet = None
                for content_field in ["content", "body", "text", "code"]:
                    if content_field in node:
                        content = node[content_field]
                        if content and isinstance(content, str):
                            # Extract a small snippet (first 150 chars)
                            content_snippet = (
                                content[:150] + "..." if len(content) > 150 else content
                            )
                            break

                # Create search result
                search_result = SearchResult(
                    id=node.get("id", "unknown"),
                    name=node.get("name", "Unnamed"),
                    type=entity_type,
                    score=item.get("score", 0.0),
                    content_snippet=content_snippet,
                    properties={
                        k: v
                        for k, v in node.items()
                        if k not in ["id", "name", "path", "filePath"]
                    },
                    path=path,
                )
                search_results.append(search_result)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return VectorResult(
                results=search_results,
                total_count=len(search_results),
                execution_time_ms=execution_time_ms,
                query_embedding_time_ms=embedding_time if embedding_time > 0 else None,
            )

        except QueryError as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vector search failed: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error in vector search: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            )

    async def find_path(self, path_request: PathRequest) -> PathResult:
        """Find paths between nodes.

        Args:
            path_request: PathRequest domain model

        Returns:
            PathResult with the found paths

        Raises:
            HTTPException: If the path finding fails
        """
        start_time = time.time()

        try:
            # Map algorithm to Cypher procedure
            algorithm_map = {
                "shortest": "shortestPath",
                "dijkstra": "dijkstra",
                "all_shortest": "allShortestPaths",
                "all_simple": "allSimplePaths",
            }
            algo = algorithm_map.get(path_request.algorithm.value, "shortestPath")

            # Map direction to Cypher syntax
            direction_map = {"outgoing": ">", "incoming": "<", "both": ""}
            dir_symbol = direction_map.get(path_request.direction.value, "")

            # Handle relationship types
            rel_types = ""
            if path_request.relationship_types:
                rel_list = "|".join(
                    [
                        t.value
                        for t in path_request.relationship_types
                        if t.value != "any"
                    ]
                )
                if rel_list:
                    rel_types = f":{rel_list}"

            # Build the query based on the algorithm
            if algo in ["shortestPath", "allShortestPaths"]:
                # For shortest path algorithms
                query = f"""
                MATCH (start), (end)
                WHERE elementId(start) = $start_id AND elementId(end) = $end_id
                CALL apoc.path.{algo}(start, end, $max_depth, 
                    $relationship_pattern) YIELD path
                RETURN path
                LIMIT $limit
                """
                params = {
                    "start_id": path_request.start_node_id,
                    "end_id": path_request.end_node_id,
                    "max_depth": path_request.max_depth,
                    "relationship_pattern": f"{rel_types}" if rel_types else "",
                    "limit": path_request.limit,
                }
            else:
                # For more complex algorithms with direction
                query = f"""
                MATCH (start), (end)
                WHERE elementId(start) = $start_id AND elementId(end) = $end_id
                CALL apoc.path.{algo}(start, end, $relationship_pattern, null, $max_depth) YIELD path
                RETURN path
                LIMIT $limit
                """
                rel_pattern = ""
                if rel_types:
                    rel_pattern = f"{rel_types}"

                params = {
                    "start_id": path_request.start_node_id,
                    "end_id": path_request.end_node_id,
                    "relationship_pattern": rel_pattern,
                    "max_depth": path_request.max_depth,
                    "limit": path_request.limit,
                }

            # Execute the query with synchronous method
            result = self.connector.execute_query(query, params=params)

            # Convert results to domain model
            paths = []
            for item in result:
                if "path" not in item:
                    continue

                path_data = item["path"]

                # Extract nodes and relationships
                path_nodes = []
                path_rels = []

                # Process nodes in the path
                if "nodes" in path_data:
                    for node in path_data["nodes"]:
                        path_node = PathNode(
                            id=node.get("id", "unknown"),
                            labels=node.get("labels", []),
                            properties={
                                k: v
                                for k, v in node.items()
                                if k not in ["id", "labels"]
                            },
                        )
                        path_nodes.append(path_node)

                # Process relationships in the path
                if "relationships" in path_data:
                    for rel in path_data["relationships"]:
                        path_rel = PathRelationship(
                            id=rel.get("id", "unknown"),
                            type=rel.get("type", "unknown"),
                            properties={
                                k: v
                                for k, v in rel.items()
                                if k not in ["id", "type", "startNode", "endNode"]
                            },
                            start_node_id=rel.get("startNode", "unknown"),
                            end_node_id=rel.get("endNode", "unknown"),
                        )
                        path_rels.append(path_rel)

                # Create the Path object
                cost = path_data.get("cost") if "cost" in path_data else None
                path_obj = Path(
                    nodes=path_nodes,
                    relationships=path_rels,
                    length=len(path_rels),
                    cost=cost,
                )
                paths.append(path_obj)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return PathResult(
                paths=paths,
                execution_time_ms=execution_time_ms,
                total_paths_found=len(paths),
            )

        except QueryError as e:
            logger.error(f"Path finding failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path finding failed: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error in path finding: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            )


class DummyNeo4jConnector:
    """Dummy Neo4j connector for use when connection to Neo4j fails.
    
    This allows basic service functionality without Neo4j available.
    """
    
    def __init__(self):
        """Initialize the dummy connector."""
        logger.warning("Using DummyNeo4jConnector - Neo4j functionality will be limited")
    
    def check_connection(self) -> Dict[str, Any]:
        """Return dummy connection info."""
        return {
            "database": "dummy",
            "components": ["Dummy Neo4j Connector"],
        }
    
    def close(self) -> None:
        """Dummy close method."""
        pass
    
    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None, write: bool = False
    ) -> List[Dict[str, Any]]:
        """Return dummy query results."""
        logger.info(f"DummyNeo4jConnector.execute_query called with: {query[:100]}...")
        # Return empty result
        return []


class DummyNeo4jAdapter(Neo4jAdapter):
    """Neo4j adapter that uses a dummy connector.
    
    This allows basic service functionality without Neo4j being available.
    """
    
    def __init__(self):
        """Initialize with a dummy connector."""
        self.connector = DummyNeo4jConnector()


async def get_neo4j_adapter() -> Neo4jAdapter:
    """Factory function to create a Neo4j adapter.

    This is used as a FastAPI dependency.

    Returns:
        Neo4jAdapter instance (real or dummy)
    """
    try:
        # Try to create a real adapter
        adapter = Neo4jAdapter()
        # Test the connection
        await adapter.check_health()
        return adapter
    except Exception as e:
        # Log the error but don't fail
        logger.warning(f"Failed to create real Neo4j adapter: {str(e)}")
        logger.warning("Falling back to dummy Neo4j adapter for demo purposes")
        
        # Return a dummy adapter instead
        return DummyNeo4jAdapter()
