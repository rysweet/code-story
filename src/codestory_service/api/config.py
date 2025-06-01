"""API routes for configuration management.

This module provides endpoints for reading and updating configuration settings.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..application.config_service import ConfigService, get_config_service
from ..domain.config import ConfigDump, ConfigPatch, ConfigSchema
from ..infrastructure.msal_validator import get_current_user, require_role

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/config", tags=["config"])


@router.get(
    "",
    response_model=ConfigDump,
    summary="Get configuration",
    description="Get the current configuration settings.",
)
def get_config(
    include_sensitive: bool = Query(
        False, description="Whether to include sensitive values (requires admin role)"
    ),
    config_service: ConfigService = Depends(get_config_service),
    user: dict[str, Any] = Depends(get_current_user),
) -> ConfigDump:
    """Get the current configuration.

    Args:
        include_sensitive: Whether to include sensitive values
        config_service: Config service instance
        user: Current authenticated user

    Returns:
        ConfigDump with configuration values and metadata

    Raises:
        HTTPException: If retrieving configuration fails
    """
    # Check if user has permission to see sensitive values
    if include_sensitive:
        user_roles = user.get("roles", [])
        if "admin" not in user_roles:
            logger.warning(
                f"User {user.get('name')} attempted to view sensitive config values"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewing sensitive configuration values requires admin role",
            )

    try:
        logger.info("Getting configuration")
        config = config_service.get_config_dump(include_sensitive=include_sensitive)

        # Always redact sensitive values for non-admins or when not explicitly requested
        if not include_sensitive:
            config = config.redact_sensitive()

        return config
    except Exception as e:
        logger.error(f"Error getting configuration: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting configuration: {e!s}",
        ) from e


@router.patch(
    "",
    response_model=ConfigDump,
    summary="Update configuration",
    description="Update configuration settings.",
)
async def update_config(
    patch: ConfigPatch,
    config_service: ConfigService = Depends(get_config_service),
    user: dict[str, Any] = Depends(require_role(["admin"])),
) -> ConfigDump:
    """Update configuration settings.

    Args:
        patch: Configuration changes to apply
        config_service: Config service instance
        user: Current authenticated user (must have admin role)

    Returns:
        ConfigDump with the updated configuration

    Raises:
        HTTPException: If the configuration update fails
    """
    try:
        logger.info(f"Updating configuration with {len(patch.items)} changes")
        return await config_service.update_config(patch)
    except Exception as e:
        logger.error(f"Error updating configuration: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating configuration: {e!s}",
        ) from e


@router.get(
    "/schema",
    response_model=ConfigSchema,
    summary="Get configuration schema",
    description="Get the JSON Schema for the configuration.",
)
def get_config_schema(
    config_service: ConfigService = Depends(get_config_service),
    user: dict[str, Any] = Depends(get_current_user),
) -> ConfigSchema:
    """Get the JSON Schema for the configuration.

    Args:
        config_service: Config service instance
        user: Current authenticated user

    Returns:
        ConfigSchema with JSON Schema for the configuration

    Raises:
        HTTPException: If retrieving schema fails
    """
    try:
        logger.info("Getting configuration schema")
        return config_service.get_config_schema()
    except Exception as e:
        logger.error(f"Error getting configuration schema: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting configuration schema: {e!s}",
        ) from e
