"""API routes for graph operations.

This module provides endpoints for querying the graph database, including
Cypher queries, vector search, path finding, and natural language queries.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..application.graph_service import GraphService, get_graph_service
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
from ..infrastructure.msal_validator import get_current_user, require_role

# Set up logging
logger = logging.getLogger(__name__)

# Create router for query endpoints
query_router = APIRouter(prefix="/v1/query", tags=["query"])

# Create router for ask endpoint
ask_router = APIRouter(prefix="/v1/ask", tags=["ask"])


@query_router.post(
    "/cypher",
    response_model=QueryResult,
    summary="Execute Cypher query",
    description="Execute a raw Cypher query against the graph database.",
)
async def execute_cypher_query(
    query: CypherQuery,
    graph_service: GraphService = Depends(get_graph_service),
    user: dict = Depends(get_current_user),
) -> QueryResult:
    """Execute a Cypher query against the graph database.

    Args:
        query: Cypher query details
        graph_service: Graph service instance
        user: Current authenticated user

    Returns:
        QueryResult with the results of the query

    Raises:
        HTTPException: If the query execution fails
    """
    # Check if user has permission for write queries
    if query.query_type.value == "write":
        # Only allow users with admin role to execute write queries
        user_roles = user.get("roles", [])
        if "admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Write queries require admin permissions",
            )

    try:
        logger.info(f"Executing Cypher query: {query.query[:100]}...")
        return await graph_service.execute_cypher_query(query)
    except Exception as e:
        logger.error(f"Error executing Cypher query: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing query: {str(e)}",
        )


@query_router.post(
    "/vector",
    response_model=VectorResult,
    summary="Vector similarity search",
    description="Search for nodes with vector embeddings similar to the query.",
)
async def execute_vector_search(
    query: VectorQuery,
    graph_service: GraphService = Depends(get_graph_service),
    user: dict = Depends(get_current_user),
) -> VectorResult:
    """Execute a vector similarity search.

    Args:
        query: Vector search query
        graph_service: Graph service instance
        user: Current authenticated user

    Returns:
        VectorResult with the search results

    Raises:
        HTTPException: If the search fails
    """
    try:
        logger.info(f"Executing vector search: {query.query[:100]}...")
        return await graph_service.execute_vector_search(query)
    except Exception as e:
        logger.error(f"Error executing vector search: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing vector search: {str(e)}",
        )


@query_router.post(
    "/path",
    response_model=PathResult,
    summary="Find paths between nodes",
    description="Find paths between nodes in the graph.",
)
async def find_path(
    path_request: PathRequest,
    graph_service: GraphService = Depends(get_graph_service),
    user: dict = Depends(get_current_user),
) -> PathResult:
    """Find paths between nodes in the graph.

    Args:
        path_request: Path finding request
        graph_service: Graph service instance
        user: Current authenticated user

    Returns:
        PathResult with the found paths

    Raises:
        HTTPException: If the path finding fails
    """
    try:
        logger.info(
            f"Finding paths from {path_request.start_node_id} to "
            f"{path_request.end_node_id}"
        )
        return await graph_service.find_path(path_request)
    except Exception as e:
        logger.error(f"Error finding paths: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding paths: {str(e)}",
        )


@ask_router.post(
    "",
    response_model=AskAnswer,
    summary="Ask a question about the codebase",
    description="Ask a natural language question about the codebase.",
)
async def ask_question(
    request: AskRequest,
    graph_service: GraphService = Depends(get_graph_service),
    user: dict = Depends(get_current_user),
) -> AskAnswer:
    """Answer a natural language question about the codebase.

    Args:
        request: The question and parameters
        graph_service: Graph service instance
        user: Current authenticated user

    Returns:
        AskAnswer with the generated answer

    Raises:
        HTTPException: If answering fails
    """
    try:
        logger.info(f"Answering question: {request.question}")
        return await graph_service.answer_question(request)
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error answering question: {str(e)}",
        )
