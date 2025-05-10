"""Unit tests for the MCP Adapter authentication."""

from unittest import mock

import pytest

from codestory_mcp.auth.entra_validator import AuthenticationError, AuthorizationError, EntraValidator
from codestory_mcp.auth.scope_manager import ScopeManager


class TestScopeManager:
    """Tests for the ScopeManager class."""

    def test_get_required_scopes(self):
        """Test getting required scopes."""
        # Create a mock settings object
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["scope1", "scope2"]

        manager = ScopeManager(settings=mock_settings)
        assert manager.get_required_scopes() == ["scope1", "scope2"]

    def test_has_required_scope_when_no_scopes_required(self):
        """Test that any scopes are accepted when no scopes are required."""
        # Create a mock settings object
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = []

        manager = ScopeManager(settings=mock_settings)
        assert manager.has_required_scope([]) is True
        assert manager.has_required_scope(["random-scope"]) is True

    def test_has_required_scope_with_wildcard(self):
        """Test that wildcard scope grants access to all scopes."""
        # Create a mock settings object
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["scope1", "scope2"]

        manager = ScopeManager(settings=mock_settings)
        assert manager.has_required_scope(["*"]) is True

    def test_has_required_scope_with_matching_scope(self):
        """Test that having one required scope is sufficient."""
        # Create a mock settings object
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["scope1", "scope2"]

        manager = ScopeManager(settings=mock_settings)
        assert manager.has_required_scope(["scope1"]) is True
        assert manager.has_required_scope(["scope2"]) is True
        assert manager.has_required_scope(["scope1", "other-scope"]) is True

    def test_has_required_scope_with_no_matching_scope(self):
        """Test that having no required scope results in denial."""
        # Create a mock settings object
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["scope1", "scope2"]

        manager = ScopeManager(settings=mock_settings)
        assert manager.has_required_scope([]) is False
        assert manager.has_required_scope(["other-scope"]) is False

    def test_can_execute_tool(self):
        """Test tool execution authorization."""
        # Create a mock settings object
        mock_settings = mock.MagicMock()
        mock_settings.required_scopes = ["code-story.read", "code-story.query"]

        manager = ScopeManager(settings=mock_settings)

        # With required scope
        assert manager.can_execute_tool("anyTool", ["code-story.read"]) is True

        # Without required scope
        assert manager.can_execute_tool("anyTool", ["wrong-scope"]) is False


class TestEntraValidator:
    """Tests for the EntraValidator class."""
    
    @pytest.fixture
    def mock_jwks_client(self):
        """Create a mock JWKS client."""
        with mock.patch("codestory_mcp.auth.entra_validator.PyJWKClient") as mock_client:
            yield mock_client
    
    @pytest.fixture
    def mock_jwt(self):
        """Create a mock JWT module."""
        with mock.patch("codestory_mcp.auth.entra_validator.jwt") as mock_jwt:
            yield mock_jwt
    
    @pytest.fixture
    def validator(self, mock_jwks_client):
        """Create an EntraValidator instance."""
        return EntraValidator("test-tenant", "test-audience")
    
    def test_init(self, mock_jwks_client):
        """Test initialization."""
        validator = EntraValidator("test-tenant", "test-audience")
        
        assert validator.tenant_id == "test-tenant"
        assert validator.audience == "test-audience"
        mock_jwks_client.assert_called_once_with(
            "https://login.microsoftonline.com/test-tenant/discovery/v2.0/keys"
        )
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, validator, mock_jwt):
        """Test successful token validation."""
        # Mock the key from JWKS client
        mock_key = mock.Mock()
        validator.jwks_client.get_signing_key_from_jwt.return_value = mock_key
        
        # Mock JWT decode
        mock_jwt.decode.return_value = {
            "sub": "test-user",
            "azp": "test-client",
            "scp": "code-story.read code-story.query"
        }
        
        # Patch scope verification
        with mock.patch.object(validator, "_verify_scopes") as mock_verify:
            claims = await validator.validate_token("test-token")
            
            # Verify key retrieval
            validator.jwks_client.get_signing_key_from_jwt.assert_called_once_with("test-token")
            
            # Verify JWT decode
            mock_jwt.decode.assert_called_once_with(
                "test-token",
                mock_key.key,
                algorithms=["RS256"],
                audience="test-audience",
                options={"verify_signature": True}
            )
            
            # Verify scope verification
            mock_verify.assert_called_once_with(mock_jwt.decode.return_value)
            
            # Verify claims
            assert claims == mock_jwt.decode.return_value
    
    @pytest.mark.asyncio
    async def test_validate_token_jwt_error(self, validator, mock_jwt):
        """Test token validation with JWT error."""
        # Make JWT decode raise an error
        mock_jwt.PyJWTError = Exception
        validator.jwks_client.get_signing_key_from_jwt.side_effect = mock_jwt.PyJWTError("Invalid token")
        
        # Verify error handling
        with pytest.raises(AuthenticationError) as excinfo:
            await validator.validate_token("invalid-token")
        
        assert "Token validation failed" in str(excinfo.value)
    
    def test_verify_scopes_success(self, validator):
        """Test successful scope verification."""
        # Mock ScopeManager
        with mock.patch.object(
            validator.scope_manager, "has_required_scope", return_value=True
        ) as mock_has_scope:
            # Claims with string scope
            validator._verify_scopes({"scp": "code-story.read"})
            mock_has_scope.assert_called_with(["code-story.read"])
            
            # Claims with list scope
            validator._verify_scopes({"scope": ["code-story.query"]})
            mock_has_scope.assert_called_with(["code-story.query"])
    
    def test_verify_scopes_failure(self, validator):
        """Test scope verification failure."""
        # Mock ScopeManager
        with mock.patch.object(
            validator.scope_manager, "has_required_scope", return_value=False
        ):
            # Verify error is raised
            with pytest.raises(AuthorizationError) as excinfo:
                validator._verify_scopes({"scp": "wrong-scope"})
            
            assert "Token lacks required scopes" in str(excinfo.value)