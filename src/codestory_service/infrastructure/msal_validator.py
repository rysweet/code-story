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
logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

class MSALValidator:
    """Validator for MSAL JWT tokens.

    This class handles validation of JWT tokens issued by Microsoft Entra ID,
    extracting claims and ensuring the token is valid and not expired.
    """

    def __init__(self: Any) -> None:
        """Initialize the MSAL validator."""
        self.settings = get_service_settings()
        self.dev_mode = self.settings.dev_mode
        self.auth_enabled = self.settings.auth_enabled
        if self.dev_mode:
            self.auth_enabled = False
            logger.info('Development mode enabled - authentication will be bypassed')
        if not self.auth_enabled:
            logger.warning('Running with authentication DISABLED. This should only be used for local development.')
        self.jwt_secret = None
        if self.settings.jwt_secret:
            self.jwt_secret = self.settings.jwt_secret.get_secret_value()
        self.jwt_algorithm = self.settings.jwt_algorithm

    async def validate_token(self: Any, token: str) -> dict[str, Any]:
        """Validate a JWT token and return the claims.

        Args:
            token: JWT token to validate

        Returns:
            Dictionary of claims from the token

        Raises:
            HTTPException: If token validation fails
        """
        if not self.auth_enabled:
            if not token:
                return {'sub': 'anonymous', 'name': 'Anonymous User', 'roles': ['user'], 'exp': int(time.time() + 3600)}
            try:
                claims = jwt.decode(token, options={'verify_signature': False, 'verify_exp': False})
                return claims
            except Exception:
                return {'sub': 'anonymous', 'name': 'Anonymous User', 'roles': ['user'], 'exp': int(time.time() + 3600)}
        if self.dev_mode and self.jwt_secret:
            try:
                claims = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                return claims
            except jwt.ExpiredSignatureError as err:
                logger.warning('Token has expired')
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token has expired', headers={'WWW-Authenticate': 'Bearer'}) from err
            except jwt.InvalidTokenError as e:
                logger.warning(f'Invalid token: {e!s}')
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f'Invalid token: {e!s}', headers={'WWW-Authenticate': 'Bearer'}) from e
        logger.error('Full MSAL validation not implemented')
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Full MSAL validation not implemented')

    async def create_dev_token(self: Any, username: str, roles: list[str] | None=None) -> str:
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
        if roles is None:
            roles = ['user']
        if not self.dev_mode:
            logger.error('Token creation only available in development mode')
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Token creation only available in development mode')
        if not self.jwt_secret:
            logger.error('JWT secret not configured')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='JWT secret not configured')
        try:
            now = int(time.time())
            payload = {'sub': username, 'name': username, 'roles': roles, 'iat': now, 'exp': now + self.settings.jwt_expiration, 'iss': 'codestory-dev', 'aud': 'codestory-api'}
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            return token
        except Exception as e:
            logger.error(f'Failed to create token: {e!s}')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Failed to create token: {e!s}') from e

async def get_msal_validator() -> MSALValidator:
    """Factory function to create an MSAL validator.

    This is used as a FastAPI dependency.

    Returns:
        MSALValidator instance
    """
    return MSALValidator()

async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None=Depends(security), validator: MSALValidator=Depends(get_msal_validator)) -> dict[str, Any]:
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
    dev_user = {'sub': 'dev-user', 'name': 'Development User', 'roles': ['admin', 'user'], 'exp': int(time.time() + 3600)}
    if not validator.auth_enabled:
        logger.info('Using development user due to auth_enabled=False')
        return dev_user
    if credentials is None:
        if validator.dev_mode:
            logger.warning('No authentication credentials provided. Using development user in dev mode.')
            return dev_user
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication credentials missing', headers={'WWW-Authenticate': 'Bearer'})
    try:
        token = credentials.credentials
        claims = await validator.validate_token(token)
        return claims
    except HTTPException as e:
        if validator.dev_mode:
            logger.warning(f'Auth error in dev mode: {e.detail}. Using development user instead.')
            return dev_user
        raise

async def get_optional_user(request: Request, credentials: HTTPAuthorizationCredentials | None=Depends(security), validator: MSALValidator=Depends(get_msal_validator)) -> dict[str, Any] | None:
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
    if not validator.auth_enabled or validator.dev_mode:
        dev_user = {'sub': 'dev-user', 'name': 'Development User', 'roles': ['admin', 'user'], 'exp': int(time.time() + 3600)}
        logger.debug('Using development user for optional authentication')
        return dev_user
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(request, credentials, validator)
    except HTTPException:
        return None

def require_role(required_roles: list[str]) -> Any:
    """Create a dependency that requires the user to have one of the specified roles.

    Args:
        required_roles: List of roles, any of which grants access

    Returns:
        A dependency function that validates the user's roles

    Raises:
        HTTPException: If the user doesn't have any of the required roles
    """

    async def role_checker(user: dict[str, Any]=Depends(get_current_user)) -> dict[str, Any]:
        user_roles = user.get('roles', [])
        if any((role in user_roles for role in required_roles)):
            return user
        logger.warning(f"Access denied: User {user.get('name')} with roles {user_roles} does not have any of the required roles {required_roles}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')
    return role_checker

async def is_admin(user: dict[str, Any]=Depends(get_current_user)) -> dict[str, Any]:
    """Check if the current user has admin role.

    Args:
        user: User claims dictionary

    Returns:
        The user claims if the user is an admin

    Raises:
        HTTPException: If the user doesn't have admin role
    """
    user_roles = user.get('roles', [])
    if 'admin' in user_roles:
        return user
    logger.warning(f"Admin access denied: User {user.get('name')} with roles {user_roles} does not have the admin role")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Administrative privileges required')