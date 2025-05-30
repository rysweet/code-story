"""API routes for authentication.

This module provides endpoints for user authentication and token management.
These endpoints are mainly used in development mode.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..application.auth_service import AuthService, get_auth_service
from ..domain.auth import LoginRequest, TokenResponse, UserInfo
from ..infrastructure.msal_validator import get_optional_user
from ..settings import get_service_settings

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description=(
        "Login with username and password to get a JWT token. "
        "Only available in development mode."
    ),
)
async def login(
    request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """Authenticate a user and generate a token.

    This endpoint is only available in development mode.

    Args:
        request: Login credentials
        auth_service: Auth service instance

    Returns:
        TokenResponse with the generated token

    Raises:
        HTTPException: If authentication fails or is not available
    """
    settings = get_service_settings()

    if not settings.dev_mode:
        logger.warning("Attempt to use local login in production mode")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local login is only available in development mode",
        )

    try:
        logger.info(f"Login attempt for user: {request.username}")
        return await auth_service.login(request)
    except Exception as e:
        logger.error(f"Login failed: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {e!s}",
        ) from e


@router.get(
    "/whoami",
    response_model=UserInfo,
    summary="Get current user info",
    description="Get information about the currently authenticated user.",
)
async def get_user_info(
    auth_service: AuthService = Depends(get_auth_service),
    user: dict[str, Any] | None = Depends(get_optional_user),
) -> UserInfo:
    """Get information about the current user.

    Args:
        auth_service: Auth service instance
        user: Current authenticated user (optional)

    Returns:
        UserInfo with user details
    """
    if not user:
        return UserInfo(id="anonymous", name="Anonymous User", roles=[], is_authenticated=False)[call-arg]  # type: ignore[call-arg]

    try:
        logger.info(f"Getting info for user: {user.get('name', 'unknown')}")
        return await auth_service.get_user_info(user)
    except Exception as e:
        logger.error(f"Error getting user info: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user info: {e!s}",
        ) from e