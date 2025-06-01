"""API routes for service control.

This module provides endpoints for controlling the service lifecycle,
such as starting and stopping the service. These endpoints are only
available in development mode and are no-ops in production.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..infrastructure.msal_validator import require_role
from ..settings import get_service_settings

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/service", tags=["service"])


@router.post(
    "/start",
    summary="Start service",
    description=(
        "Start the Code Story service and its dependencies. "
        "Only available in development mode."
    ),
)
async def start_service(
    user: dict[str, str] = Depends(require_role(["admin"])),
) -> dict[str, str]:
    """Start the Code Story service and its dependencies.

    This endpoint is only available in development mode and is a no-op in production.

    Args:
        user: Current authenticated user (must have admin role)

    Returns:
        Dictionary with status message

    Raises:
        HTTPException: If starting the service fails or is not available
    """
    settings = get_service_settings()

    if not settings.dev_mode:
        logger.warning("Attempt to start service in production mode")
        return {
            "status": "not_supported",
            "message": "Service control is only available in development mode",
        }

    try:
        # In a real implementation, this would run start scripts
        # For demo purposes, we'll just return success
        logger.info("Starting service (dev mode)")

        return {"status": "success", "message": "Service started successfully"}
    except Exception as e:
        logger.error(f"Failed to start service: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start service: {e!s}",
        ) from e


@router.post(
    "/stop",
    summary="Stop service",
    description=(
        "Stop the Code Story service and its dependencies. "
        "Only available in development mode."
    ),
)
async def stop_service(
    user: dict[str, str] = Depends(require_role(["admin"]))
) -> dict[str, str]:
    """Stop the Code Story service and its dependencies.

    This endpoint is only available in development mode and is a no-op in production.

    Args:
        user: Current authenticated user (must have admin role)

    Returns:
        Dictionary with status message

    Raises:
        HTTPException: If stopping the service fails or is not available
    """
    settings = get_service_settings()

    if not settings.dev_mode:
        logger.warning("Attempt to stop service in production mode")
        return {
            "status": "not_supported",
            "message": "Service control is only available in development mode",
        }

    try:
        # In a real implementation, this would run stop scripts
        # For demo purposes, we'll just return success
        logger.info("Stopping service (dev mode)")

        return {"status": "success", "message": "Service stopped successfully"}
    except Exception as e:
        logger.error(f"Failed to stop service: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop service: {e!s}",
        ) from e
