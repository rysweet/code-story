import os
print(f"[main.py startup] CODESTORY_SERVICE__PORT={os.environ.get('CODESTORY_SERVICE__PORT')}, PORT={os.environ.get('PORT')}, CODESTORY_TEST_PORT={os.environ.get('CODESTORY_TEST_PORT')}", flush=True)
print("[service startup] main.py loaded (VERY TOP)", flush=True)
import os
print(f"[service startup] CODESTORY_SERVICE__PORT in os.environ: {os.environ.get('CODESTORY_SERVICE__PORT')}", flush=True)
print(f"[DEBUG] CODESTORY_SERVICE__PORT={os.environ.get('CODESTORY_SERVICE__PORT')}, PORT={os.environ.get('PORT')}")
from codestory.config.settings import get_settings
print(f"[DEBUG] get_settings().service.port={get_settings().service.port}")
print("[service startup] ENVIRONMENT VARIABLES (TOP):", flush=True)
for k, v in sorted(os.environ.items()):
    print(f"{k}={v}", flush=True)
from codestory.config.settings import get_settings
print(f"[service startup] get_settings().service.port (TOP): {get_settings().service.port}", flush=True)
import sys
print(f"[service startup] sys.executable: {sys.executable}", flush=True)
print(f"[service startup] sys.path: {sys.path}", flush=True)
# DEBUG: Print all environment variables at startup
import os
import time
print("SERVICE CONTAINER ENVIRONMENT VARIABLES:", flush=True)
for k, v in sorted(os.environ.items()):
    print(f"{k}={v}", flush=True)
print("END ENVIRONMENT VARIABLES", flush=True)
print("OPENAI ENV VARS:", flush=True)
for k, v in sorted(os.environ.items()):
    if "OPENAI" in k or "AZURE" in k:
        print(f"{k}={v}", flush=True)
print("END OPENAI ENV VARS", flush=True)
# (Removed container-only debug file write: /app/service_env_debug.txt)
import os
print(f"[DEBUG] CODESTORY_NEO4J__URI at startup: {os.environ.get('CODESTORY_NEO4J__URI')}")
print("[service startup] All environment variables:", flush=True)
for k, v in sorted(os.environ.items()):
    print(f"{k}={v}", flush=True)
# Health check: wait for Neo4j to be ready before starting the backend

try:
    # Prefer environment variable, then local, then container path
    config_paths = []
    env_path = os.environ.get("TEST_CONFIG_PATH")
    if env_path:
        config_paths.append(env_path)
    config_paths.append("tests/fixtures/test_config.toml")
    config_paths.append("/app/tests/fixtures/test_config.toml")
    found = False
    for path in config_paths:
        try:
            with open(path) as f:
                print(f"[service startup] test_config.toml contents from {path}:", flush=True)
                print(f.read(), flush=True)
                found = True
                break
        except Exception:
            continue
    if not found:
        print(f"[service startup] Could not read test_config.toml from any known location: {config_paths}", flush=True)
except Exception as e:
    print(f"[service startup] Unexpected error reading test_config.toml: {e}", flush=True)
print(f"[service startup] CODESTORY_NEO4J__URI in os.environ: {os.environ.get('CODESTORY_NEO4J__URI')}", flush=True)
try:
    from codestory_service.settings import get_settings
    print(f"[service startup] get_settings().neo4j.uri: {get_settings().neo4j.uri}", flush=True)
    print(f"[service startup] get_settings().service.port: {get_settings().service.port}", flush=True)
except Exception as e:
    print(f"[service startup] Error loading settings: {e}", flush=True)
"""Main entry point for Code Story API service."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Optional

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
    logging.error(
        "Service requires all components to be available for proper operation"
    )
    raise RuntimeError(f"Failed to initialize required adapters: {e!s}") from e

# Set up logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print("[main.py] lifespan() context manager entered", flush=True)
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
            "Using '*' for CORS origins in non-development environment. This is a security risk!"
        )

    # Log dev mode and auth status
    logger.info(
        f"Service running in {'development' if settings.dev_mode else 'production'} mode"
    )
    logger.info(
        f"Authentication {'disabled' if not settings.auth_enabled else 'enabled'}"
    )

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
        logger.warning(
            f"Neo4j connection check failed: {e}. Service may have limited functionality."
        )

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
    print("[main.py] create_app() called", flush=True)
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
        request: Request,
        type: str = Query("force"),
        theme: str = Query("auto"),
        graph_service: GraphService = Depends(get_graph_service),
        user: dict[str, Any] | None = Depends(get_optional_user),
    ) -> HTMLResponse:
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
                logger.warning(
                    f"Invalid visualization type: {type}, using default: force"
                )

            viz_theme = VisualizationTheme.AUTO
            try:
                viz_theme = VisualizationTheme(theme)
            except ValueError:
                logger.warning(
                    f"Invalid visualization theme: {theme}, using default: auto"
                )

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
            ) from e

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
# Always create the app at the top level for ASGI servers
app = create_app()

# Add this block to run the server when this module is executed directly
if __name__ == "__main__":
    import sys
    print(f"[service startup] sys.executable: {sys.executable}", flush=True)
    print(f"[service startup] sys.path: {sys.path}", flush=True)
    # DEBUG: Print all environment variables at startup
    import os
    import time
    print("SERVICE CONTAINER ENVIRONMENT VARIABLES:", flush=True)
    for k, v in sorted(os.environ.items()):
        print(f"{k}={v}", flush=True)
    print("END ENVIRONMENT VARIABLES", flush=True)
    print("OPENAI ENV VARS:", flush=True)
    for k, v in sorted(os.environ.items()):
        if "OPENAI" in k or "AZURE" in k:
            print(f"{k}={v}", flush=True)
    print("END OPENAI ENV VARS", flush=True)
    # (Removed container-only debug file write: /app/service_env_debug.txt)
    print(f"[DEBUG] CODESTORY_NEO4J__URI at startup: {os.environ.get('CODESTORY_NEO4J__URI')}")
    print("[service startup] All environment variables:", flush=True)
    # Health check: wait for Neo4j to be ready before starting the backend
    try:
        # Prefer environment variable, then local, then container path
        config_paths = []
        env_path = os.environ.get("TEST_CONFIG_PATH")
        if env_path:
            config_paths.append(env_path)
        config_paths.append("tests/fixtures/test_config.toml")
        config_paths.append("/app/tests/fixtures/test_config.toml")
        found = False
        for path in config_paths:
            try:
                with open(path) as f:
                    print(f"[service startup] test_config.toml contents from {path}:", flush=True)
                    print(f.read(), flush=True)
                    found = True
                    break
            except Exception:
                continue
        if not found:
            print(f"[service startup] Could not read test_config.toml from any known location: {config_paths}", flush=True)
    except Exception as e:
        print(f"[service startup] Unexpected error reading test_config.toml: {e}", flush=True)
    print(f"[service startup] CODESTORY_NEO4J__URI in os.environ: {os.environ.get('CODESTORY_NEO4J__URI')}", flush=True)
    try:
        from codestory_service.settings import get_settings
        print(f"[service startup] get_settings().neo4j.uri: {get_settings().neo4j.uri}", flush=True)
    except Exception as e:
        print(f"[service startup] Error loading settings: {e}", flush=True)

    # Health check: wait for Neo4j to be ready before starting the backend
    try:
        from neo4j import GraphDatabase
        from neo4j.exceptions import ServiceUnavailable
        uri = os.environ.get("CODESTORY_NEO4J__URI") or os.environ.get("NEO4J_URI")
        username = os.environ.get("CODESTORY_NEO4J__USERNAME") or os.environ.get("NEO4J_USERNAME", "neo4j")
        password = os.environ.get("CODESTORY_NEO4J__PASSWORD") or os.environ.get("NEO4J_PASSWORD") or "password"
        print(f"[main.py] Health check: Using uri={uri}, username={username}, password={password}")
        for attempt in range(30):
            try:
                driver = GraphDatabase.driver(uri, auth=(username, password))
                with driver.session() as session:
                    result = session.run("RETURN 1 AS ready")
                    if result.single()["ready"] == 1:
                        print("[main.py] Neo4j is ready.")
                        break
            except ServiceUnavailable as e:
                print(f"[main.py] Waiting for Neo4j to be ready... ({e})")
                time.sleep(1)
        else:
            print("[main.py] Neo4j did not become ready in time.")
            sys.exit(1)
        driver.close()
    except Exception as e:
        print(f"[main.py] Error during Neo4j health check: {e}")
        sys.exit(1)

    import uvicorn

    # --- Wait for Redis to be ready before starting the backend ---
    try:
        import redis
        redis_uri = os.environ.get("CODESTORY_REDIS__URI") or os.environ.get("REDIS__URI") or "redis://localhost:6379/0"
        print(f"[main.py] Health check: Using redis_uri={redis_uri}")
        for attempt in range(30):
            try:
                client = redis.Redis.from_url(redis_uri, socket_connect_timeout=2)
                client.ping()
                print("[main.py] Redis is ready.")
                break
            except Exception as e:
                print(f"[main.py] Waiting for Redis to be ready... ({e})")
                time.sleep(1)
        else:
            print("[main.py] Redis did not become ready in time.")
            sys.exit(1)
        client.close()
    except Exception as e:
        print(f"[main.py] Error during Redis health check: {e}")
        sys.exit(1)

    from codestory.config.settings import get_settings

    core_settings = get_settings()
    host = core_settings.service.host
    port = core_settings.service.port
    print(f"Starting service on {host}:{port}...")
    print("[service startup] BACKEND FULLY STARTED AND READY TO SERVE REQUESTS", flush=True)
    import threading
    def print_ready():
        import time
        for _ in range(30):
            print("[service startup] (heartbeat) BACKEND IS RUNNING", flush=True)
            time.sleep(2)
    threading.Thread(target=print_ready, daemon=True).start()
    print("[service startup] If you see this message, the backend process is about to call uvicorn.run()", flush=True)
    uvicorn.run("src.codestory_service.main:app", host=host, port=port, reload=False)
