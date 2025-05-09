"""Main entry point for Code Story API service."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from .api import auth, config, graph, health, ingest, service, websocket
from .infrastructure.neo4j_adapter import Neo4jConnector
from .settings import get_service_settings

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
    app.state.db = Neo4jConnector()
    await app.state.db.check_connection_async()

    yield

    # Clean up resources
    logger.info("Cleaning up application resources")

    # Close Neo4j connection
    if hasattr(app.state, "db"):
        await app.state.db.close_async()


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

    # Backward compatibility health check
    @app.get("/health")
    async def legacy_health_check() -> Dict[str, str]:
        """Legacy health check endpoint.

        Returns:
            Simple health status
        """
        return {"status": "healthy"}

    return app


# Create the application instance
app = create_app()
