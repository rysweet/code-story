"""MCP Server implementation.

This module implements the Model Context Protocol (MCP) server
for the Code Story knowledge graph.
"""

import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from prometheus_client import make_asgi_app

from codestory_mcp.auth.entra_validator import EntraValidator
from codestory_mcp.tools import get_all_tools, get_tool
from codestory_mcp.tools.base import ToolError
from codestory_mcp.utils.config import get_mcp_settings
from codestory_mcp.utils.metrics import get_metrics

# Configure structured logging
logger = structlog.get_logger(__name__)


# Authentication dependency
async def get_current_user(request: Request) -> dict[str, Any]:
    """Get the current authenticated user.

    Args:
        request: FastAPI request

    Returns:
        User information

    Raises:
        HTTPException: If authentication fails
    """
    settings = get_mcp_settings()
    metrics = get_metrics()

    # Skip authentication if disabled
    if not settings.auth_enabled:
        logger.warning("Authentication is disabled", security="none")
        return {"sub": "anonymous", "name": "Anonymous User", "scopes": ["*"]}

    # Get bearer token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        metrics.record_auth_attempt("error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ")[1]

    # Validate token
    try:
        validator = EntraValidator(settings.azure_tenant_id, settings.api_audience)
        claims = await validator.validate_token(token)
        metrics.record_auth_attempt("success")
        return claims
    except Exception as e:
        metrics.record_auth_attempt("error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Tool execution wrapper
def tool_executor(func: Callable) -> Callable:
    """Wrapper for tool execution.

    This decorator wraps tool execution with error handling,
    parameter validation, and metrics collection.

    Args:
        func: Tool execution function

    Returns:
        Wrapped function
    """

    @wraps(func)
    async def wrapper(
        tool_name: str,
        params: dict[str, Any],
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        metrics = get_metrics()
        start_time = time.time()

        try:
            # Get the tool
            tool_class = get_tool(tool_name)
            tool = tool_class()

            # Validate parameters
            tool.validate_parameters(params)

            # Execute tool
            result = await tool(params)

            # Record metrics
            duration = time.time() - start_time
            metrics.record_tool_call(tool_name, "success", duration)

            return result
        except KeyError as err:
            metrics.record_tool_call(tool_name, "error", time.time() - start_time)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_name}",
            ) from err
        except ToolError as e:
            metrics.record_tool_call(tool_name, "error", time.time() - start_time)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            ) from e
        except HTTPException:
            metrics.record_tool_call(tool_name, "error", time.time() - start_time)
            raise
        except Exception as e:
            metrics.record_tool_call(tool_name, "error", time.time() - start_time)
            logger.exception("Tool execution error", tool_name=tool_name, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tool execution error: {e!s}",
            ) from e

    return wrapper


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan handler.

    This context manager handles startup and shutdown events.

    Args:
        app: FastAPI application
    """
    # Startup: Initialize resources
    logger.info("Starting MCP server")

    # Yield control to the application
    yield

    # Shutdown: Clean up resources
    logger.info("Shutting down MCP server")


def create_app() -> FastAPI:
    """Create the FastAPI application.

    Returns:
        FastAPI application
    """
    settings = get_mcp_settings()

    # Create the FastAPI application
    app = FastAPI(
        title="Code Story MCP",
        description="Model Context Protocol server for Code Story knowledge graph",
        version="0.1.0",
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add Prometheus metrics
    app.mount(
        settings.prometheus_metrics_path,
        make_asgi_app(),
        name="metrics",
    )

    # Create API router
    router = APIRouter(prefix="/v1")

    # Tool call endpoint
    @router.post(
        "/tools/{tool_name}",
        summary="Execute a tool",
        description="Execute a tool with the given parameters",
        response_model=dict[str, Any],
    )
    @tool_executor
    async def execute_tool(
        tool_name: str,
        params: dict[str, Any],
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        """Execute a tool with the given parameters.

        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            user: Current user (from auth)

        Returns:
            Tool execution results
        """
        # This is just a placeholder - the actual execution is handled by the decorator
        pass

    # Get available tools endpoint
    @router.get(
        "/tools",
        summary="Get available tools",
        description="Get a list of available tools and their schemas",
    )
    async def get_tools(
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, list[dict[str, Any]]]:
        """Get a list of available tools and their schemas.

        Args:
            user: Current user (from auth)

        Returns:
            List of available tools
        """
        tools = get_all_tools()

        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in tools
            ]
        }

    # Health check endpoint
    @router.get(
        "/health",
        summary="Health check",
        description="Check if the MCP server is healthy",
    )
    async def health_check() -> dict[str, str]:
        """Health check.

        Returns:
            Health status
        """
        return {"status": "healthy"}

    # Add router to app
    app.include_router(router)

    # Add custom error handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle generic exceptions.

        Args:
            request: FastAPI request
            exc: Exception

        Returns:
            JSON response with error details
        """
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        if isinstance(exc, HTTPException):
            status_code = exc.status_code
            # For FastAPI's HTTPException, format error in the way our tests expect
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": {
                        "message": str(exc.detail),
                        "type": exc.__class__.__name__,
                    }
                },
            )

        logger.exception(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "message": str(exc),
                    "type": exc.__class__.__name__,
                }
            },
        )

    return app


def run_server() -> None:
    """Run the MCP server.

    This function is the entry point for running the server.
    """
    import uvicorn

    settings = get_mcp_settings()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Run the server
    uvicorn.run(
        "codestory_mcp.server:create_app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        factory=True,
        log_level="info" if not settings.debug else "debug",
    )


if __name__ == "__main__":
    run_server()
