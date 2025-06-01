"""Authentication service for Code Story Service.

This module provides application-level services for authentication and authorization,
including token validation, user management, and role-based access control.
"""
import logging
from typing import Any

from fastapi import Depends, HTTPException, status

from ..domain.auth import LoginRequest, TokenResponse, UserInfo
from ..infrastructure.msal_validator import MSALValidator, get_msal_validator
from ..settings import get_service_settings

logger = logging.getLogger(__name__)


class AuthService:
    """Application service for authentication and authorization.

    This service provides methods for authenticating users,
    validating tokens, and checking permissions.
    """

    def __init__(self: Any, msal_validator: MSALValidator) -> None:
        """Initialize the authentication service.

        Args:
            msal_validator: MSAL validator instance
        """
        self.validator = msal_validator
        self.settings = get_service_settings()

    async def login(self: Any, request: LoginRequest) -> TokenResponse:
        """Authenticate a user and generate a token.

        This is only available in development mode.

        Args:
            request: Login credentials

        Returns:
            TokenResponse with the generated token

        Raises:
            HTTPException: If authentication fails or is not available
        """
        if not self.settings.dev_mode:
            logger.error("Login endpoint only available in development mode")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Login endpoint only available in development mode",
            )
        try:
            if request.username == "admin" and request.password == "password":
                token = await self.validator.create_dev_token(
                    request.username, roles=["admin", "user"]
                )
                return TokenResponse(
                    access_token=token,
                    token_type="Bearer",
                    expires_in=self.settings.jwt_expiration,
                    scope="api",
                )
            elif request.username == "user" and request.password == "password":
                token = await self.validator.create_dev_token(
                    request.username, roles=["user"]
                )
                return TokenResponse(
                    access_token=token,
                    token_type="Bearer",
                    expires_in=self.settings.jwt_expiration,
                    scope="api",
                )
            else:
                logger.warning(f"Invalid login attempt for user {request.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            logger.error(f"Login failed: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Login failed: {e!s}",
            ) from e

    async def get_user_info(self: Any, claims: dict[str, Any]) -> UserInfo:
        """Get information about the current user.

        Args:
            claims: User claims from the token

        Returns:
            UserInfo with user details
        """
        return UserInfo(
            id=claims.get("sub", "unknown"),
            name=claims.get("name", "Unknown User"),
            email=claims.get("email"),
            roles=claims.get("roles", []),
            is_authenticated=True,
        )

    def check_permission(
        self: Any, claims: dict[str, Any], required_roles: list[str]
    ) -> bool:
        """Check if the user has the required permissions.

        Args:
            claims: User claims from the token
            required_roles: List of roles that grant access

        Returns:
            True if the user has permission, False otherwise
        """
        user_roles = claims.get("roles", [])
        return any(role in user_roles for role in required_roles)


async def get_auth_service(
    msal_validator: MSALValidator = Depends(get_msal_validator),
) -> AuthService:
    """Factory function to create an authentication service.

    This is used as a FastAPI dependency.

    Args:
        msal_validator: MSAL validator instance

    Returns:
        AuthService instance
    """
    return AuthService(msal_validator)
