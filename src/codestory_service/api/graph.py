"""API routes for graph operations.

This module provides endpoints for querying the graph database, including
Cypher queries, vector search, path finding, and natural language queries.
It also provides visualization endpoints for generating graph visualizations.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from ..application.graph_service import GraphService, get_graph_service
from ..domain.graph import (
    AskAnswer,
    AskRequest,
    CypherQuery,
    DatabaseClearRequest,
    DatabaseClearResponse,
    PathRequest,
    PathResult,
    QueryResult,
    VectorQuery,
    VectorResult,
    VisualizationRequest,
    VisualizationTheme,
    VisualizationType,
)
from ..infrastructure.msal_validator import get_current_user, get_optional_user, is_admin

# Set up logging
logger = logging.getLogger(__name__)

# Create router for query endpoints
query_router = APIRouter(prefix="/v1/query", tags=["query"])

# Create router for ask endpoint
ask_router = APIRouter(prefix="/v1/ask", tags=["ask"])

# Create router for visualization endpoint
visualization_router = APIRouter(prefix="/v1/visualize", tags=["visualization"])

# Create router for database management endpoint
db_router = APIRouter(prefix="/v1/database", tags=["database"])


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
        logger.error(f"Error executing Cypher query: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing query: {e!s}",
        ) from e


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
        logger.error(f"Error executing vector search: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing vector search: {e!s}",
        ) from e


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
        logger.error(f"Error finding paths: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding paths: {e!s}",
        ) from e


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
        logger.error(f"Error answering question: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error answering question: {e!s}",
        ) from e


@visualization_router.get(
    "",
    response_class=HTMLResponse,
    summary="Generate graph visualization",
    description="Generate an interactive HTML visualization of the code graph.",
)
async def generate_visualization(
    type: VisualizationType = Query(
        VisualizationType.FORCE, description="Type of visualization"
    ),
    theme: VisualizationTheme = Query(
        VisualizationTheme.AUTO, description="Color theme"
    ),
    focus_node_id: str | None = Query(
        None, description="Node ID to focus on"
    ),
    depth: int = Query(
        2, description="Depth of relationships to include from focus node", ge=1, le=5
    ),
    max_nodes: int = Query(
        100, description="Maximum number of nodes to display initially", ge=10, le=500
    ),
    node_types: str | None = Query(
        None, description="Comma-separated list of node types to include"
    ),
    search_query: str | None = Query(
        None, description="Text search to filter nodes"
    ),
    include_orphans: bool = Query(
        False, description="Whether to include nodes with no connections"
    ),
    graph_service: GraphService = Depends(get_graph_service),
    user: dict = Depends(get_optional_user),
) -> HTMLResponse:
    """Generate an interactive HTML visualization of the code graph.

    Args:
        type: Type of visualization (force, hierarchy, radial, sankey)
        theme: Color theme (light, dark, auto)
        focus_node_id: Node ID to focus the visualization on
        depth: Depth of relationships to include from focus node
        max_nodes: Maximum number of nodes to display initially
        node_types: Comma-separated list of node types to include
        search_query: Text search to filter nodes
        include_orphans: Whether to include nodes with no connections
        graph_service: Graph service instance
        user: Current authenticated user

    Returns:
        HTMLResponse with the graph visualization

    Raises:
        HTTPException: If visualization generation fails
    """
    try:
        logger.info(f"Generating graph visualization of type: {type}, theme: {theme}")
        
        # Parse node_types if provided
        parsed_node_types = None
        if node_types:
            parsed_node_types = [nt.strip() for nt in node_types.split(",")]
        
        # Create visualization request
        has_custom_filter = (
            parsed_node_types or 
            search_query is not None or 
            max_nodes != 100 or 
            include_orphans
        )
        
        request = VisualizationRequest(
            type=type,
            theme=theme,
            focus_node_id=focus_node_id,
            depth=depth,
            filter={
                "node_types": parsed_node_types,
                "search_query": search_query,
                "max_nodes": max_nodes,
                "include_orphans": include_orphans,
            } if has_custom_filter else None
        )
        
        # Generate HTML
        html_content = await graph_service.generate_visualization(request)
        return HTMLResponse(content=html_content, media_type="text/html")
    except Exception as e:
        logger.error(f"Error generating visualization: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating visualization: {e!s}",
        ) from e


# Legacy endpoint for backward compatibility with CLI - redirects to the v1 endpoint
# This is mounted at the root level in main.py
@visualization_router.get(
    "/legacy",
    response_class=HTMLResponse,
    summary="Generate graph visualization (legacy endpoint)",
    description="Legacy endpoint for generating an interactive HTML visualization.",
    include_in_schema=False  # Hide from API docs
)
async def generate_visualization_legacy(
    type: str = Query("force", description="Type of visualization"),
    theme: str = Query("auto", description="Color theme"),
    graph_service: GraphService = Depends(get_graph_service),
    user: dict = Depends(get_optional_user),
) -> HTMLResponse:
    """Legacy endpoint for generating an interactive HTML visualization of the code graph.

    This is for backward compatibility with the CLI and GUI.

    Args:
        type: Type of visualization (force, hierarchy, radial, sankey)
        theme: Color theme (light, dark, auto)
        graph_service: Graph service instance
        user: Current authenticated user

    Returns:
        HTMLResponse with the graph visualization
    """
    # Convert string params to enum values
    viz_type = VisualizationType.FORCE
    try:
        viz_type = VisualizationType(type)
    except ValueError:
        logger.warning(f"Invalid visualization type: {type}, using default: force")
    
    viz_theme = VisualizationTheme.AUTO
    try:
        viz_theme = VisualizationTheme(theme)
    except ValueError:
        logger.warning(f"Invalid visualization theme: {theme}, using default: auto")
    
    # Create visualization request with limited parameters for backward compatibility
    request = VisualizationRequest(
        type=viz_type,
        theme=viz_theme,
    )
    
    # Generate HTML
    try:
        html_content = await graph_service.generate_visualization(request)
        return HTMLResponse(content=html_content, media_type="text/html")
    except Exception as e:
        logger.error(f"Error generating visualization: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating visualization: {e!s}",
        ) from e
            
            
@db_router.post(
    "/clear",
    response_model=DatabaseClearResponse,
    summary="Clear database",
    description="Clear all data from the database. Requires admin privileges.",
)
async def clear_database(
    request: DatabaseClearRequest,
    graph_service: GraphService = Depends(get_graph_service),
    user: dict = Depends(is_admin),  # Require admin privileges
) -> DatabaseClearResponse:
    """Clear all data from the database.
    
    This is a destructive operation that will delete all nodes and relationships.
    Schema constraints and indexes can be preserved.
    
    Args:
        request: Clear request parameters, includes confirmation
        graph_service: Graph service instance
        user: Current admin user
        
    Returns:
        DatabaseClearResponse with operation status
        
    Raises:
        HTTPException: If the operation fails or user lacks permissions
    """
    try:
        logger.warning(f"Database clear requested by user: {user.get('name', 'unknown')}")
        return await graph_service.clear_database(request)
    except Exception as e:
        logger.error(f"Error clearing database: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing database: {e!s}",
        )
