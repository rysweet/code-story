"""Tests for the configuration export functionality."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from pydantic import SecretStr

from src.codestory.config import (
    Settings,
    export_to_json,
    export_to_toml,
    create_env_template,
    settings_to_dict,
)
from src.codestory.config.export import _redact_secrets


@pytest.fixture
def mock_settings():
    """Fixture to provide a mock Settings instance."""
    settings = MagicMock(spec=Settings)
    
    # Create mock nested settings
    settings.app_name = "code-story"
    settings.version = "0.1.0"
    settings.environment = "development"
    
    # Mock neo4j settings
    settings.neo4j = MagicMock()
    settings.neo4j.uri = "bolt://localhost:7687"
    settings.neo4j.username = "neo4j"
    settings.neo4j.password = SecretStr("password")
    
    # Mock redis settings
    settings.redis = MagicMock()
    settings.redis.uri = "redis://localhost:6379"
    
    # Mock openai settings
    settings.openai = MagicMock()
    settings.openai.api_key = SecretStr("test-key")
    settings.openai.embedding_model = "text-embedding-3-small"
    
    # Mock service settings
    settings.service = MagicMock()
    settings.service.host = "0.0.0.0"
    settings.service.port = 8000
    
    # Model dump method
    settings.model_dump.return_value = {
        "app_name": "code-story",
        "version": "0.1.0",
        "environment": "development",
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password",
        },
        "redis": {
            "uri": "redis://localhost:6379",
        },
        "openai": {
            "api_key": "test-key",
            "embedding_model": "text-embedding-3-small",
        },
        "service": {
            "host": "0.0.0.0",
            "port": 8000,
        },
    }
    
    return settings


def test_redact_secrets():
    """Test redacting secrets from configuration dictionaries."""
    config = {
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password",
        },
        "openai": {
            "api_key": "test-key",
            "embedding_model": "text-embedding-3-small",
        },
        "azure": {
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
    }
    
    redacted = _redact_secrets(config)
    
    # Assert passwords and keys are redacted
    assert redacted["neo4j"]["password"] == "********"
    assert redacted["openai"]["api_key"] == "********"
    assert redacted["azure"]["client_secret"] == "********"
    
    # Assert non-sensitive values are preserved
    assert redacted["neo4j"]["uri"] == "bolt://localhost:7687"
    assert redacted["neo4j"]["username"] == "neo4j"
    assert redacted["openai"]["embedding_model"] == "text-embedding-3-small"
    assert redacted["azure"]["client_id"] == "client-id"


def test_settings_to_dict(mock_settings):
    """Test converting settings to a dictionary."""
    # Test with redaction (default)
    result = settings_to_dict(mock_settings)
    
    # Assert structure is preserved
    assert "neo4j" in result
    assert "redis" in result
    assert "openai" in result
    
    # Assert sensitive values are redacted
    assert result["neo4j"]["password"] == "********"
    assert result["openai"]["api_key"] == "********"
    
    # Test without redaction
    result = settings_to_dict(mock_settings, redact_secrets=False)
    
    # Assert sensitive values are not redacted
    assert result["neo4j"]["password"] == "password"
    assert result["openai"]["api_key"] == "test-key"


def test_export_to_json(mock_settings):
    """Test exporting settings to JSON."""
    with patch("src.codestory.config.export.get_settings", return_value=mock_settings):
        # Test with default parameters
        json_str = export_to_json()
        
        # Parse the JSON string
        data = json.loads(json_str)
        
        # Assert structure is preserved
        assert "neo4j" in data
        assert "redis" in data
        assert "openai" in data
        
        # Assert sensitive values are redacted
        assert data["neo4j"]["password"] == "********"
        assert data["openai"]["api_key"] == "********"
        
        # Test with output to file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            export_to_json(output_path=tmp_path, redact_secrets=False)
            
            # Read and parse the file
            with open(tmp_path, "r") as f:
                data = json.load(f)
            
            # Assert sensitive values are not redacted
            assert data["neo4j"]["password"] == "password"
            assert data["openai"]["api_key"] == "test-key"
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def test_export_to_toml(mock_settings):
    """Test exporting settings to TOML."""
    with patch("src.codestory.config.export.get_settings", return_value=mock_settings):
        # Test with default parameters
        toml_str = export_to_toml()
        
        # Check content
        assert "neo4j" in toml_str
        assert "redis" in toml_str
        assert "openai" in toml_str
        
        # Assert sensitive values are redacted
        assert "password = " not in toml_str
        assert "********" in toml_str
        
        # Test with output to file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            export_to_toml(output_path=tmp_path, redact_secrets=False)
            
            # Read the file
            with open(tmp_path, "r") as f:
                content = f.read()
            
            # Assert sensitive values are not redacted
            assert 'password = "password"' in content.replace(" ", "")
            assert 'api_key = "test-key"' in content.replace(" ", "")
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def test_create_env_template(mock_settings):
    """Test creating an .env template."""
    with patch("src.codestory.config.export.get_settings", return_value=mock_settings):
        # Test with default parameters
        env_template = create_env_template()
        
        # Check content
        assert "APP_NAME=code-story" in env_template
        assert "VERSION=0.1.0" in env_template
        assert "ENVIRONMENT=development" in env_template
        assert "NEO4J__URI=bolt://localhost:7687" in env_template
        assert "NEO4J__USERNAME=neo4j" in env_template
        assert "NEO4J__PASSWORD=your-password-here" in env_template
        assert "REDIS__URI=redis://localhost:6379" in env_template
        
        # Assert comments are included by default
        assert "# Core settings" in env_template
        assert "# Neo4j settings" in env_template
        
        # Test with output to file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            create_env_template(output_path=tmp_path, include_comments=False)
            
            # Read the file
            with open(tmp_path, "r") as f:
                content = f.read()
            
            # Assert content is correct
            assert "APP_NAME=code-story" in content
            assert "NEO4J__PASSWORD=your-password-here" in content
            
            # Assert comments are not included
            assert "# Core settings" not in content
            assert "# Neo4j settings" not in content
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)