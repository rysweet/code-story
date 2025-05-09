"""Graph service for Code Story Service.

This module provides application-level services for interacting with
the graph database, including query execution, vector search, and
path finding.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import Depends, HTTPException, status

from ..domain.graph import (
    CypherQuery,
    QueryResult,
    VectorQuery,
    VectorResult,
    PathRequest,
    PathResult,
    AskRequest,
    AskAnswer,
)
from ..infrastructure.neo4j_adapter import Neo4jAdapter, get_neo4j_adapter
from ..infrastructure.openai_adapter import OpenAIAdapter, get_openai_adapter

# Set up logging
logger = logging.getLogger(__name__)


class GraphService:
    """Application service for graph operations.

    This service orchestrates interactions with the graph database,
    providing high-level methods for the API layer.
    """

    def __init__(
        self, neo4j_adapter: Neo4jAdapter, openai_adapter: OpenAIAdapter
    ) -> None:
        """Initialize the graph service.

        Args:
            neo4j_adapter: Neo4j adapter instance
            openai_adapter: OpenAI adapter instance
        """
        self.neo4j = neo4j_adapter
        self.openai = openai_adapter

    async def execute_cypher_query(self, query: CypherQuery) -> QueryResult:
        """Execute a Cypher query against the graph database.

        Args:
            query: Cypher query details

        Returns:
            QueryResult with the results of the query

        Raises:
            HTTPException: If the query execution fails
        """
        try:
            logger.info(f"Executing Cypher query: {query.query[:100]}...")
            result = await self.neo4j.execute_cypher_query(query)
            logger.info(f"Query returned {result.row_count} rows")
            return result
        except Exception as e:
            logger.error(f"Error executing Cypher query: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing query: {str(e)}",
            )

    async def execute_vector_search(self, query: VectorQuery) -> VectorResult:
        """Execute a vector similarity search.

        Args:
            query: Vector search query

        Returns:
            VectorResult with the search results

        Raises:
            HTTPException: If the search fails
        """
        try:
            # First, generate embedding for the query text
            logger.info(f"Generating embedding for vector search: {query.query}")
            embeddings = await self.openai.create_embeddings([query.query])

            if not embeddings or len(embeddings) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate embedding for query",
                )

            # Execute the search with the generated embedding
            logger.info(f"Executing vector search for entity type: {query.entity_type}")
            result = await self.neo4j.execute_vector_search(query, embeddings[0])
            logger.info(f"Vector search returned {result.total_count} results")
            return result
        except Exception as e:
            logger.error(f"Error executing vector search: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing vector search: {str(e)}",
            )

    async def find_path(self, path_request: PathRequest) -> PathResult:
        """Find paths between nodes in the graph.

        Args:
            path_request: Path finding request

        Returns:
            PathResult with the found paths

        Raises:
            HTTPException: If the path finding fails
        """
        try:
            logger.info(
                f"Finding paths from {path_request.start_node_id} to "
                f"{path_request.end_node_id} using algorithm {path_request.algorithm}"
            )
            result = await self.neo4j.find_path(path_request)
            logger.info(f"Path finding returned {result.total_paths_found} paths")
            return result
        except Exception as e:
            logger.error(f"Error finding paths: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error finding paths: {str(e)}",
            )

    async def answer_question(self, request: AskRequest) -> AskAnswer:
        """Answer a natural language question about the codebase.

        Args:
            request: The question and parameters

        Returns:
            AskAnswer with the generated answer

        Raises:
            HTTPException: If answering fails
        """
        try:
            # First, generate embedding for the question
            logger.info(f"Generating embedding for question: {request.question}")
            embeddings = await self.openai.create_embeddings([request.question])

            if not embeddings or len(embeddings) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate embedding for question",
                )

            # Search for relevant context in the graph
            context_size = request.context_size or 5

            # Create a query to find relevant nodes
            vector_query = VectorQuery(
                query=request.question,
                entity_type=None,  # Search across all entity types
                limit=context_size,
                min_score=0.5,  # Minimum relevance threshold
            )

            # Execute the search
            search_result = await self.neo4j.execute_vector_search(
                vector_query, embeddings[0]
            )

            # Retrieve full content for each context item
            context_items = []
            for result in search_result.results:
                # Fetch the full node with all properties
                node_query = CypherQuery(
                    query="MATCH (n) WHERE elementId(n) = $id RETURN n",
                    parameters={"id": result.id},
                    query_type="read",
                )

                node_result = await self.neo4j.execute_cypher_query(node_query)

                if (
                    node_result.rows
                    and len(node_result.rows) > 0
                    and len(node_result.rows[0]) > 0
                ):
                    node = node_result.rows[0][0]  # First column of first row
                    node["score"] = result.score  # Add the relevance score
                    context_items.append(node)

            # Generate the answer using the OpenAI adapter
            logger.info(f"Generating answer using {len(context_items)} context items")
            answer = await self.openai.answer_question(request, context_items)

            logger.info("Answer generated successfully")
            return answer
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error answering question: {str(e)}",
            )


async def get_graph_service(
    neo4j: Neo4jAdapter = Depends(get_neo4j_adapter),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> GraphService:
    """Factory function to create a graph service.

    This is used as a FastAPI dependency.

    Args:
        neo4j: Neo4j adapter instance
        openai: OpenAI adapter instance

    Returns:
        GraphService instance
    """
    return GraphService(neo4j, openai)
