"""JWT token validator for Microsoft Entra ID.

This module provides functions for validating JWT tokens issued by Microsoft Entra ID.
"""
from typing import Any
import jwt
import structlog
from jwt.jwks_client import PyJWKClient
from codestory_mcp.auth.scope_manager import ScopeManager
logger = structlog.get_logger(__name__)

class AuthenticationError(Exception):
    """Authentication error."""

    def __init__(self: Any, message: str) -> None:
        """Initialize the error.

        Args:
            message: Error message
        """
        self.message = message
        super().__init__(message)

class AuthorizationError(Exception):
    """Authorization error."""

    def __init__(self: Any, message: str) -> None:
        """Initialize the error.

        Args:
            message: Error message
        """
        self.message = message
        super().__init__(message)

class EntraValidator:
    """JWT token validator for Microsoft Entra ID."""

    def __init__(self: Any, tenant_id: str, audience: str, scope_manager: Any=None, jwks_client: Any=None) -> None:
        """Initialize the validator.

        Args:
            tenant_id: Microsoft Entra ID tenant ID
            audience: Expected audience claim
            scope_manager: Optional scope manager instance
            jwks_client: Optional JWKS client instance
        """
        self.tenant_id = tenant_id
        self.audience = audience
        self.jwks_client = jwks_client or PyJWKClient(f'https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys')
        self.scope_manager = scope_manager or ScopeManager()

    async def validate_token(self: Any, token: str) -> dict[str, Any]:
        """Validate JWT token and return claims if valid.

        Args:
            token: JWT token to validate

        Returns:
            Token claims

        Raises:
            AuthenticationError: If token validation fails
            AuthorizationError: If token lacks required scopes
        """
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(token, signing_key.key, algorithms=['RS256'], audience=self.audience, options={'verify_signature': True})
            logger.info('Token validated successfully', sub=claims.get('sub', 'unknown'), client_id=claims.get('azp', 'unknown'))
            self._verify_scopes(claims)
            return claims
        except jwt.PyJWTError as e:
            logger.warning('Token validation failed', error=str(e))
            raise AuthenticationError(f'Token validation failed: {e!s}') from e
        except Exception as e:
            logger.exception('Unexpected error during token validation')
            raise AuthenticationError(f'Token validation failed: {e!s}') from e

    def _verify_scopes(self: Any, claims: dict[str, Any]) -> None:
        """Verify the token contains required scopes.

        Args:
            claims: Token claims

        Raises:
            AuthorizationError: If token lacks required scopes
        """
        raw_scopes = claims.get('scp', claims.get('scope', ''))
        if isinstance(raw_scopes, str):
            scopes = raw_scopes.split()
        elif isinstance(raw_scopes, list):
            scopes = raw_scopes
        else:
            scopes: list[Any] = []
        if not self.scope_manager.has_required_scope(scopes):
            logger.warning('Token lacks required scopes', provided_scopes=scopes, required_scopes=self.scope_manager.get_required_scopes())
            raise AuthorizationError('Token lacks required scopes')