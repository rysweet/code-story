"""MSAL validator for handling authentication in the Code Story Service.

This module provides integration with Microsoft Authentication Library (MSAL)
for validating JWT tokens and authenticating users against Microsoft Entra ID
(formerly Azure AD).
"""

import logging
import time
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..settings import get_service_settings

# Set up logging
logger = logging.getLogger(__name__)

# Define security scheme for token extraction
# Allow auto error to be disabled in dev mode to prevent 401 errors
security = HTTPBearer(auto_error=False)


class MSALValidator:
    """Validator for MSAL JWT tokens.

    This class handles validation of JWT tokens issued by Microsoft Entra ID,
    extracting claims and ensuring the token is valid and not expired.
    """

    def __init__(self) -> None:
        """Initialize the MSAL validator."""
        self.settings = get_service_settings()

        # Determine if we're in development mode with simplified auth
        self.dev_mode = self.settings.dev_mode
        self.auth_enabled = self.settings.auth_enabled
        
        # For better compatibility, consider auth disabled in dev mode
        if self.dev_mode:
            self.auth_enabled = False
            logger.info("Development mode enabled - authentication will be bypassed")
            
        if not self.auth_enabled:
            logger.warning(
                "Running with authentication DISABLED. "
                "This should only be used for local development."
            )

        # For dev mode with simplified JWT validation
        self.jwt_secret = None
        if self.settings.jwt_secret:
            self.jwt_secret = self.settings.jwt_secret.get_secret_value()

        self.jwt_algorithm = self.settings.jwt_algorithm

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate a JWT token and return the claims.

        Args:
            token: JWT token to validate

        Returns:
            Dictionary of claims from the token

        Raises:
            HTTPException: If token validation fails
        """
        if not self.auth_enabled:
            # In dev mode with auth disabled, accept any token or return default claims
            if not token:
                return {
                    "sub": "anonymous",
                    "name": "Anonymous User",
                    "roles": ["user"],
                    "exp": int(time.time() + 3600),
                }

            # Try to decode the token, but don't enforce validation
            try:
                claims = jwt.decode(
                    token, options={"verify_signature": False, "verify_exp": False}
                )
                return claims
            except Exception:
                return {
                    "sub": "anonymous",
                    "name": "Anonymous User",
                    "roles": ["user"],
                    "exp": int(time.time() + 3600),
                }

        # Dev mode with simplified JWT validation
        if self.dev_mode and self.jwt_secret:
            try:
                claims = jwt.decode(
                    token, self.jwt_secret, algorithms=[self.jwt_algorithm]
                )
                return claims
            except jwt.ExpiredSignatureError:
                logger.warning("Token has expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid token: {e!s}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {e!s}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Production mode with full MSAL validation
        # This is just a placeholder - in a real implementation, we would use
        # the MSAL library to validate the token against Azure AD
        logger.error("Full MSAL validation not implemented")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Full MSAL validation not implemented",
        )

    async def create_dev_token(self, username: str, roles: list[str] = ["user"]) -> str:
        """Create a development JWT token.

        This is only available in development mode and should not be used in production.

        Args:
            username: Username to include in the token
            roles: List of roles to assign to the user

        Returns:
            JWT token string

        Raises:
            HTTPException: If token creation fails or is not available
        """
        if not self.dev_mode:
            logger.error("Token creation only available in development mode")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token creation only available in development mode",
            )

        if not self.jwt_secret:
            logger.error("JWT secret not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret not configured",
            )

        try:
            # Create a simple JWT token with basic claims
            now = int(time.time())
            payload = {
                "sub": username,
                "name": username,
                "roles": roles,
                "iat": now,
                "exp": now + self.settings.jwt_expiration,
                "iss": "codestory-dev",
                "aud": "codestory-api",
            }

            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

            return token

        except Exception as e:
            logger.error(f"Failed to create token: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create token: {e!s}",
            )


async def get_msal_validator() -> MSALValidator:
    """Factory function to create an MSAL validator.

    This is used as a FastAPI dependency.

    Returns:
        MSALValidator instance
    """
    return MSALValidator()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    validator: MSALValidator = Depends(get_msal_validator),
) -> dict[str, Any]:
    """Get the current authenticated user from the request.

    This function is used as a FastAPI dependency for protected endpoints.

    Args:
        request: FastAPI request object
        credentials: Extracted Bearer token (Optional since auto_error=False)
        validator: MSAL validator instance

    Returns:
        Dictionary of user claims

    Raises:
        HTTPException: If authentication fails and dev_mode is False
    """
    # Define dev user for simplicity
    dev_user = {
        "sub": "dev-user",
        "name": "Development User",
        "roles": ["admin", "user"],
        "exp": int(time.time() + 3600),
    }
    
    # Case 1: Authentication is disabled
    if not validator.auth_enabled:
        logger.info("Using development user due to auth_enabled=False")
        return dev_user
    
    # Case 2: No credentials provided
    if credentials is None:
        if validator.dev_mode:
            logger.warning("No authentication credentials provided. Using development user in dev mode.")
            return dev_user
        else:
            # In production mode, enforce authentication
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Case 3: Credentials provided, validate token
    try:
        token = credentials.credentials
        claims = await validator.validate_token(token)
        return claims
    except HTTPException as e:
        # If in dev mode, use dev user instead of failing
        if validator.dev_mode:
            logger.warning(f"Auth error in dev mode: {e.detail}. Using development user instead.")
            return dev_user
        # In production, raise the original error
        raise


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    validator: MSALValidator = Depends(get_msal_validator),
) -> dict[str, Any] | None:
    """Get the current user if authenticated, otherwise None.

    This function is used as a FastAPI dependency for endpoints that
    support both authenticated and anonymous access.

    Args:
        request: FastAPI request object
        credentials: Extracted Bearer token (or None)
        validator: MSAL validator instance

    Returns:
        Dictionary of user claims or None if not authenticated
    """
    # In dev mode with auth disabled, return a default user
    if not validator.auth_enabled or validator.dev_mode:
        # Define dev user for simplicity
        dev_user = {
            "sub": "dev-user",
            "name": "Development User",
            "roles": ["admin", "user"],
            "exp": int(time.time() + 3600),
        }
        logger.debug("Using development user for optional authentication")
        return dev_user
    
    # In production mode, try to authenticate or return None
    if not credentials or not credentials.credentials:
        return None

    try:
        return await get_current_user(request, credentials, validator)
    except HTTPException:
        return None


def require_role(required_roles: list[str]):
    """Create a dependency that requires the user to have one of the specified roles.

    Args:
        required_roles: List of roles, any of which grants access

    Returns:
        A dependency function that validates the user's roles

    Raises:
        HTTPException: If the user doesn't have any of the required roles
    """

    async def role_checker(
        user: dict[str, Any] = Depends(get_current_user)
    ) -> dict[str, Any]:
        user_roles = user.get("roles", [])

        # Check if the user has any of the required roles
        if any(role in user_roles for role in required_roles):
            return user

        logger.warning(
            f"Access denied: User {user.get('name')} with roles {user_roles} "
            f"does not have any of the required roles {required_roles}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    return role_checker


async def is_admin(
    user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """Check if the current user has admin role.

    Args:
        user: User claims dictionary

    Returns:
        The user claims if the user is an admin

    Raises:
        HTTPException: If the user doesn't have admin role
    """
    user_roles = user.get("roles", [])
    
    if "admin" in user_roles:
        return user
        
    logger.warning(
        f"Admin access denied: User {user.get('name')} with roles {user_roles} "
        f"does not have the admin role"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, 
        detail="Administrative privileges required"
    )
