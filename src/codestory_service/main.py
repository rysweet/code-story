"""Main entry point for Code Story API service."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from prometheus_client import make_asgi_app

from .api import auth, config, graph, health, ingest, service, websocket
from .application.graph_service import GraphService, get_graph_service
from .infrastructure.msal_validator import get_optional_user
from .infrastructure.neo4j_adapter import Neo4jConnector
from .settings import get_service_settings

# Import and apply real adapter overrides
try:
    from .use_real_adapters import apply_overrides
    # Apply the overrides to force real adapters
    apply_overrides()
    logging.info("Using real adapters for all components - mock/demo adapters disabled")
except Exception as e:
    # In normal mode, we fail if any required adapter is not available
    logging.error(f"Failed to apply real adapter overrides: {e!s}")
    logging.error("Service requires all components to be available for proper operation")
    raise RuntimeError(f"Failed to initialize required adapters: {e!s}")

# Set up logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    This handles startup and shutdown for the service, including
    initialization and cleanup of resources.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Validate settings and log warnings if needed
    settings = get_service_settings()
    if "*" in settings.cors_origins and not settings.dev_mode:
        logger.warning(
            "Using '*' for CORS origins in non-development environment. "
            "This is a security risk!"
        )
    
    # Log dev mode and auth status
    logger.info(f"Service running in {'development' if settings.dev_mode else 'production'} mode")
    logger.info(f"Authentication {'disabled' if not settings.auth_enabled else 'enabled'}")
    
    # Initialize resources
    logger.info("Initializing application resources")

    # Set up Neo4j connection
    # Use the environment variable for database name if available
    database = os.environ.get("CS_NEO4J_DATABASE", "neo4j")
    app.state.db = Neo4jConnector(database=database)
    
    # Check connection synchronously for now (no async methods available)
    # We'll need to add these methods to Neo4jConnector later
    try:
        app.state.db.check_connection()
        logger.info("Neo4j connection established successfully")
    except Exception as e:
        logger.warning(f"Neo4j connection check failed: {e}. Service may have limited functionality.")

    yield

    # Clean up resources
    logger.info("Cleaning up application resources")

    # Close Neo4j connection
    if hasattr(app.state, "db"):
        try:
            app.state.db.close()
            logger.info("Neo4j connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection: {e}")


def create_app() -> FastAPI:
    """Create the FastAPI application.

    Returns:
        FastAPI application instance
    """
    settings = get_service_settings()

    # Create the FastAPI application
    app = FastAPI(
        title=settings.title,
        summary=settings.summary,
        description="API for Code Story knowledge graph service",
        version=settings.version,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )

    # Set up CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Set up Prometheus metrics
    if settings.metrics_enabled:
        # Create metrics endpoint
        metrics_app = make_asgi_app()
        app.mount(settings.metrics_route, metrics_app)

    # Mount API routers
    app.include_router(ingest.router)
    app.include_router(graph.query_router)
    app.include_router(graph.ask_router)
    app.include_router(graph.visualization_router)
    app.include_router(graph.db_router)
    app.include_router(config.router)
    app.include_router(service.router)
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(websocket.router)
    
    # Add legacy visualization endpoint at the root level (no /v1 prefix)
    # This is for backward compatibility with the CLI and GUI
    legacy_viz_router = APIRouter(tags=["visualization"])
    
    @legacy_viz_router.get(
        "/visualize",
        response_class=HTMLResponse,
        include_in_schema=False,  # Hide from API docs
    )
    async def visualize_legacy(
        type: str = Query("force"),
        theme: str = Query("auto"),
        request: Request = None,
        graph_service: GraphService = Depends(get_graph_service),
        user: dict = Depends(get_optional_user),
    ):
        """Legacy endpoint for generating graph visualization."""
        try:
            # Convert string params to enum values
            from codestory_service.domain.graph import (
                VisualizationRequest,
                VisualizationTheme,
                VisualizationType,
            )
            
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
            viz_request = VisualizationRequest(
                type=viz_type,
                theme=viz_theme,
            )
            
            # Generate HTML content
            html_content = await graph_service.generate_visualization(viz_request)
            return HTMLResponse(content=html_content, media_type="text/html")
        except Exception as e:
            logger.error(f"Error generating visualization: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating visualization: {e!s}",
            )
    
    app.include_router(legacy_viz_router)

    # Root endpoint
    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint.

        Returns:
            Basic service information
        """
        return {
            "name": settings.title,
            "version": settings.version,
            "description": settings.summary,
        }

    return app


# Create the application instance
app = create_app()

# Add this block to run the server when this module is executed directly
if __name__ == "__main__":
    import uvicorn

    from codestory.config.settings import get_settings
    
    core_settings = get_settings()
    host = core_settings.service.host
    port = core_settings.service.port
    print(f"Starting service on {host}:{port}...")
    uvicorn.run(
        "src.codestory_service.main:app", 
        host=host, 
        port=port,
        reload=False
    )
