"""Tests for the configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from pydantic import SecretStr

from src.codestory.config import (
    Settings,
    get_settings,
    refresh_settings,
    update_config,
    get_config_value,
    export_to_json,
    create_env_template,
    SettingNotFoundError,
)


@pytest.fixture
def mock_env():
    """Fixture to provide a controlled environment for testing."""
    env_vars = {
        "NEO4J__URI": "bolt://localhost:7687",
        "NEO4J__USERNAME": "neo4j",
        "NEO4J__PASSWORD": "password",
        "REDIS__URI": "redis://localhost:6379",
        "OPENAI__API_KEY": "test-key",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        yield env_vars


@pytest.fixture
def temp_env_file():
    """Fixture to create a temporary .env file."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write("NEO4J__URI=bolt://localhost:7687\n")
        f.write("NEO4J__USERNAME=neo4j\n")
        f.write("NEO4J__PASSWORD=test-password\n")
        f.write("REDIS__URI=redis://localhost:6379\n")
        f.write("OPENAI__API_KEY=test-key\n")
        temp_path = f.name
    
    yield temp_path
    
    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_toml_file():
    """Fixture to create a temporary .codestory.toml file."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write("[neo4j]\n")
        f.write('uri = "bolt://localhost:7687"\n')
        f.write('username = "neo4j"\n')
        f.write('database = "neo4j"\n')
        f.write("[redis]\n")
        f.write('uri = "redis://localhost:6379"\n')
        temp_path = f.name
    
    yield temp_path
    
    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def test_settings_default_values(mock_env):
    """Test default values for settings."""
    settings = Settings()
    assert settings.app_name == "code-story"
    assert settings.version == "0.1.0"
    assert settings.neo4j.uri == "bolt://localhost:7687"
    assert settings.neo4j.username == "neo4j"
    assert settings.neo4j.password.get_secret_value() == "password"
    assert settings.redis.uri == "redis://localhost:6379"
    assert settings.openai.api_key.get_secret_value() == "test-key"
    assert settings.openai.embedding_model == "text-embedding-3-small"
    assert settings.service.host == "0.0.0.0"
    assert settings.service.port == 8000


def test_settings_override_from_env(mock_env):
    """Test overriding settings from environment variables."""
    with patch.dict(os.environ, {
        "NEO4J__URI": "bolt://neo4j:7687",
        "SERVICE__PORT": "9000",
        "OPENAI__EMBEDDING_MODEL": "text-embedding-3-large",
    }, clear=False):
        settings = Settings()
        assert settings.neo4j.uri == "bolt://neo4j:7687"
        assert settings.service.port == 9000
        assert settings.openai.embedding_model == "text-embedding-3-large"


def test_get_settings_cache():
    """Test that get_settings caches the result."""
    with patch("src.codestory.config.settings.Settings") as mock_settings:
        mock_settings.return_value = MagicMock()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be called only once due to caching
        assert mock_settings.call_count == 1
        assert settings1 is settings2


def test_refresh_settings():
    """Test refreshing settings clears the cache."""
    with patch("src.codestory.config.settings.Settings") as mock_settings:
        mock_settings.return_value = MagicMock()
        
        # First call
        settings1 = get_settings()
        assert mock_settings.call_count == 1
        
        # Refresh settings
        refresh_settings()
        
        # Second call should create a new instance
        settings2 = get_settings()
        assert mock_settings.call_count == 2
        assert settings1 is not settings2


def test_get_config_value(mock_env):
    """Test getting a config value by path."""
    # Get a basic string value
    assert get_config_value("neo4j.uri") == "bolt://localhost:7687"
    
    # Get a SecretStr value (should return the secret value)
    assert get_config_value("neo4j.password") == "password"
    
    # Get a nested value with dot notation in the path
    assert get_config_value("openai.embedding_model") == "text-embedding-3-small"
    
    # Test error on invalid path
    with pytest.raises(SettingNotFoundError):
        get_config_value("invalid.path")


def test_update_config(mock_env):
    """Test updating a config value in memory."""
    # Clear the cache so we start with a fresh settings instance
    refresh_settings()
    
    # Update a value in memory
    update_config("neo4j.uri", "bolt://neo4j-test:7687")
    
    # Get a fresh settings instance
    refresh_settings()
    settings = get_settings()
    
    # The value should be updated
    assert settings.neo4j.uri == "bolt://neo4j-test:7687"


def test_export_to_json(mock_env):
    """Test exporting settings to JSON."""
    json_str = export_to_json()
    
    # Verify JSON has the correct structure and values
    assert "neo4j" in json_str
    assert "redis" in json_str
    assert "bolt://localhost:7687" in json_str
    # Password should be redacted by default
    assert "password" not in json_str
    assert "********" in json_str


def test_create_env_template(mock_env):
    """Test creating an .env template."""
    env_template = create_env_template()
    
    # Verify template has the correct structure and values
    assert "NEO4J__URI=bolt://localhost:7687" in env_template
    assert "NEO4J__USERNAME=neo4j" in env_template
    # Password should be a placeholder
    assert "NEO4J__PASSWORD=your-password-here" in env_template
    assert "REDIS__URI=redis://localhost:6379" in env_template


def test_settings_validation():
    """Test validation of settings."""
    # Test valid log level
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=False):
        settings = Settings()
        assert settings.log_level == "DEBUG"
    
    # Test invalid log level
    with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}, clear=False):
        with pytest.raises(ValueError):
            Settings()
    
    # Test valid telemetry log format
    with patch.dict(os.environ, {"TELEMETRY__LOG_FORMAT": "json"}, clear=False):
        settings = Settings()
        assert settings.telemetry.log_format == "json"
    
    # Test invalid telemetry log format
    with patch.dict(os.environ, {"TELEMETRY__LOG_FORMAT": "invalid"}, clear=False):
        with pytest.raises(ValueError):
            Settings()


def test_settings_with_azure_keyvault():
    """Test settings with Azure KeyVault integration."""
    # Mock the Azure KeyVault integration
    with patch("src.codestory.config.settings.Settings._load_secrets_from_keyvault") as mock_keyvault:
        # Set up environment with KeyVault config
        with patch.dict(os.environ, {
            "NEO4J__URI": "bolt://localhost:7687",
            "NEO4J__USERNAME": "neo4j",
            "NEO4J__PASSWORD": "password",
            "REDIS__URI": "redis://localhost:6379",
            "OPENAI__API_KEY": "test-key",
            "AZURE__KEYVAULT_NAME": "test-keyvault",
        }, clear=True):
            # Create settings
            settings = Settings()
            
            # Assert KeyVault integration was called
            assert mock_keyvault.called