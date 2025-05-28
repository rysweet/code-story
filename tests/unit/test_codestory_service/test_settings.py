"""Tests for the Code Story Service settings module.

This module contains tests for the service-specific settings implementation.
"""

import os
from unittest import mock

from codestory_service.settings import ServiceSettings, get_service_settings


def test_service_settings_default_values():
    """Test that default values are set correctly."""
    settings = ServiceSettings()

    # Check that default values are set correctly
    assert settings.title == "Code Story API"
    assert settings.api_prefix == "/v1"
    assert settings.cors_origins == ["*"]
    assert settings.auth_enabled is False
    assert settings.rate_limit_enabled is True
    assert settings.metrics_enabled is True
    assert settings.dev_mode is True


def test_service_settings_from_env():
    """Test that settings can be loaded from environment variables."""
    env_vars = {
        "CODESTORY_SERVICE_TITLE": "Custom API Title",
        "CODESTORY_SERVICE_API_PREFIX": "/api/v2",
        "CODESTORY_SERVICE_CORS_ORIGINS": '["example.com", "localhost"]',  # JSON array format
        "CODESTORY_SERVICE_AUTH_ENABLED": "true",
        "CODESTORY_SERVICE_DEV_MODE": "false",
        "CODESTORY_SERVICE_METRICS_ENABLED": "false",
    }

    with mock.patch.dict(os.environ, env_vars):
        settings = ServiceSettings()

        # Check that values from environment variables were used
        assert settings.title == "Custom API Title"
        assert settings.api_prefix == "/api/v2"
        assert settings.cors_origins == ["example.com", "localhost"]
        assert settings.auth_enabled is True
        assert settings.dev_mode is False
        assert settings.metrics_enabled is False


def test_service_settings_cors_origins_parsing():
    """Test that CORS origins are correctly parsed from different formats."""
    # Test with multiple origins in JSON format
    env_vars = {
        "CODESTORY_SERVICE_CORS_ORIGINS": '["example.com", "api.example.org", "localhost:3000"]',
    }
    with mock.patch.dict(os.environ, env_vars):
        settings = ServiceSettings()
        assert settings.cors_origins == [
            "example.com",
            "api.example.org",
            "localhost:3000",
        ]

    # Test with a single origin in JSON format
    env_vars = {
        "CODESTORY_SERVICE_CORS_ORIGINS": '["example.com"]',
    }
    with mock.patch.dict(os.environ, env_vars):
        settings = ServiceSettings()
        assert settings.cors_origins == ["example.com"]

    # Test with a single wildcard in JSON format
    env_vars = {
        "CODESTORY_SERVICE_CORS_ORIGINS": '["*"]',
    }
    with mock.patch.dict(os.environ, env_vars):
        settings = ServiceSettings()
        assert settings.cors_origins == ["*"]


def test_service_settings_cors_origins_validation():
    """Test that CORS origins validator works correctly."""
    # Mock the core settings environment to be "production"
    with mock.patch(
        "codestory_service.settings.get_core_settings"
    ) as mock_get_settings:
        mock_settings = mock.MagicMock()
        mock_settings.environment = "production"
        mock_get_settings.return_value = mock_settings

        # Create settings with wildcard CORS origin in production
        env_vars = {
            "CODESTORY_SERVICE_CORS_ORIGINS": '["*"]',
        }

        with mock.patch.dict(os.environ, env_vars):
            with mock.patch("codestory_service.settings.logger") as mock_logger:
                ServiceSettings()

                # Check that a warning was logged
                mock_logger.warning.assert_called_once()
                assert "security risk" in mock_logger.warning.call_args[0][0]


def test_get_service_settings():
    """Test that get_service_settings returns a ServiceSettings instance."""
    settings = get_service_settings()
    assert isinstance(settings, ServiceSettings)
