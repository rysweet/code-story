from typing import Any

"Unit tests for the MCP Adapter authentication."
from unittest import mock

import pytest

from codestory_mcp.auth.entra_validator import (
    AuthenticationError,
    AuthorizationError,
    EntraValidator,
)
from codestory_mcp.auth.scope_manager import ScopeManager


class TestScopeManager:
    """Tests for the ScopeManager class."""

    def test_get_required_scopes(self: Any) -> None:
        """Test getting required scopes."""
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["scope1", "scope2"]
        manager = ScopeManager(settings=mock_settings)
        assert manager.get_required_scopes() == ["scope1", "scope2"]

    def test_has_required_scope_when_no_scopes_required(self: Any) -> None:
        """Test that any scopes are accepted when no scopes are required."""
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = []
        manager = ScopeManager(settings=mock_settings)
        assert manager.has_required_scope([]) is True
        assert manager.has_required_scope(["random-scope"]) is True

    def test_has_required_scope_with_wildcard(self: Any) -> None:
        """Test that wildcard scope grants access to all scopes."""
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["scope1", "scope2"]
        manager = ScopeManager(settings=mock_settings)
        assert manager.has_required_scope(["*"]) is True

    def test_has_required_scope_with_matching_scope(self: Any) -> None:
        """Test that having one required scope is sufficient."""
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["scope1", "scope2"]
        manager = ScopeManager(settings=mock_settings)
        assert manager.has_required_scope(["scope1"]) is True
        assert manager.has_required_scope(["scope2"]) is True
        assert manager.has_required_scope(["scope1", "other-scope"]) is True

    def test_has_required_scope_with_no_matching_scope(self: Any) -> None:
        """Test that having no required scope results in denial."""
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["scope1", "scope2"]
        manager = ScopeManager(settings=mock_settings)
        assert manager.has_required_scope([]) is False
        assert manager.has_required_scope(["other-scope"]) is False

    def test_can_execute_tool(self: Any) -> None:
        """Test tool execution authorization."""
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["code-story.read", "code-story.query"]
        manager = ScopeManager(settings=mock_settings)
        assert manager.can_execute_tool("anyTool", ["code-story.read"]) is True
        assert manager.can_execute_tool("anyTool", ["wrong-scope"]) is False


class TestEntraValidator:
    """Tests for the EntraValidator class."""

    @pytest.fixture
    def mock_jwks_client(self: Any) -> None:
        """Create a mock JWKS client."""
        with mock.patch(
            "codestory_mcp.auth.entra_validator.PyJWKClient"
        ) as mock_client:
            yield mock_client

    @pytest.fixture
    def mock_jwt(self: Any) -> None:
        """Create a mock JWT module."""
        with mock.patch("codestory_mcp.auth.entra_validator.jwt") as mock_jwt:
            yield mock_jwt

    @pytest.fixture
    def validator(self: Any, mock_jwks_client: Any) -> Any:
        """Create an EntraValidator instance."""
        return EntraValidator("test-tenant", "test-audience")

    def test_init(self: Any, mock_jwks_client: Any) -> None:
        """Test initialization."""
        validator = EntraValidator("test-tenant", "test-audience")
        assert validator.tenant_id == "test-tenant"
        assert validator.audience == "test-audience"
        mock_jwks_client.assert_called_once_with(
            "https://login.microsoftonline.com/test-tenant/discovery/v2.0/keys"
        )

    @pytest.mark.asyncio
    async def test_validate_token_success(
        self: Any, validator: Any, mock_jwt: Any
    ) -> None:
        """Test successful token validation."""
        mock_key = mock.Mock()
        validator.jwks_client.get_signing_key_from_jwt.return_value = mock_key
        mock_jwt.decode.return_value = {
            "sub": "test-user",
            "azp": "test-client",
            "scp": "code-story.read code-story.query",
        }
        with mock.patch.object(validator, "_verify_scopes") as mock_verify:
            claims = await validator.validate_token("test-token")
            validator.jwks_client.get_signing_key_from_jwt.assert_called_once_with(
                "test-token"
            )
            mock_jwt.decode.assert_called_once_with(
                "test-token",
                mock_key.key,
                algorithms=["RS256"],
                audience="test-audience",
                options={"verify_signature": True},
            )
            mock_verify.assert_called_once_with(mock_jwt.decode.return_value)
            assert claims == mock_jwt.decode.return_value

    @pytest.mark.asyncio
    async def test_validate_token_jwt_error(
        self: Any, validator: Any, mock_jwt: Any
    ) -> None:
        """Test token validation with JWT error."""
        mock_jwt.PyJWTError = Exception
        validator.jwks_client.get_signing_key_from_jwt.side_effect = (
            mock_jwt.PyJWTError("Invalid token")
        )
        with pytest.raises(AuthenticationError) as excinfo:
            await validator.validate_token("invalid-token")
        assert "Token validation failed" in str(excinfo.value)

    def test_verify_scopes_success(self: Any, validator: Any) -> None:
        """Test successful scope verification."""
        with mock.patch.object(
            validator.scope_manager, "has_required_scope", return_value=True
        ) as mock_has_scope:
            validator._verify_scopes({"scp": "code-story.read"})
            mock_has_scope.assert_called_with(["code-story.read"])
            validator._verify_scopes({"scope": ["code-story.query"]})
            mock_has_scope.assert_called_with(["code-story.query"])

    def test_verify_scopes_failure(self: Any, validator: Any) -> None:
        """Test scope verification failure."""
        with mock.patch.object(
            validator.scope_manager, "has_required_scope", return_value=False
        ):
            with pytest.raises(AuthorizationError) as excinfo:
                validator._verify_scopes({"scp": "wrong-scope"})
            assert "Token lacks required scopes" in str(excinfo.value)
