"""Main entry point for Code Story API service."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from .api import auth, config, graph, health, ingest, service, websocket
from .infrastructure.neo4j_adapter import Neo4jConnector
from .settings import get_service_settings

# Import and apply real adapter overrides
try:
    from .use_real_adapters import apply_overrides
    # Apply the overrides to force real adapters
    apply_overrides()
    logging.info("Using real adapters for all components - mock/demo adapters disabled")
except Exception as e:
    logging.warning(f"Failed to apply real adapter overrides: {str(e)}")
    logging.warning("Service may fall back to dummy adapters if components are unavailable")

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
    app.include_router(config.router)
    app.include_router(service.router)
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(health.legacy_router)  # Add legacy health router
    app.include_router(websocket.router)

    # Root endpoint
    @app.get("/")
    async def root() -> Dict[str, str]:
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
