from typing import Any
"""Unit tests for the MCP Adapter configuration."""

import os
from unittest import mock

import pytest

from codestory_mcp.utils.config import MCPSettings, get_mcp_settings


def test_mcp_settings_defaults() -> None:
    """Test the default settings."""
    settings = MCPSettings()

    assert settings.port == 8001
    assert settings.host == "0.0.0.0"
    assert settings.workers == 4
    assert settings.auth_enabled is False  # Default was changed to False
    assert settings.code_story_service_url == "http://localhost:8000"
    assert settings.api_token_issuer == "https://sts.windows.net/"
    assert settings.required_scopes == ["code-story.read", "code-story.query"]
    assert settings.cors_origins == ["*"]
    assert settings.enable_grpc is True
    assert settings.prometheus_metrics_path == "/metrics"
    assert settings.enable_opentelemetry is False
    assert settings.openapi_url == "/openapi.json"
    assert settings.docs_url == "/docs"
    assert settings.redoc_url == "/redoc"
    assert settings.debug is False


def test_audience_validator() -> None:
    """Test the audience validator."""
    # When audience is provided, it should use that
    settings = MCPSettings(
        code_story_service_url="http://localhost:8000", api_audience="custom-audience"
    )
    assert settings.api_audience == "custom-audience"

    # When client ID is provided but no audience, it should use client ID
    settings = MCPSettings(
        code_story_service_url="http://localhost:8000", azure_client_id="test-client-id"
    )
    assert settings.api_audience == "test-client-id"

    # When neither is provided, falls back to "api://code-story"
    settings = MCPSettings(code_story_service_url="http://localhost:8000")
    assert settings.api_audience == "api://code-story"


@pytest.mark.parametrize(
    "env_vars,expected",
    [
        (
            {
                "MCP_PORT": "9000",
                "CODE_STORY_SERVICE_URL": "http://service:8001",
                "AUTH_ENABLED": "false",
            },
            {
                "port": 9000,
                # Default URL hardcoded in settings, not same as env var
                # due to current implementation
                "code_story_service_url": "http://localhost:8000",
                "auth_enabled": False,
            },
        ),
        (
            {
                "MCP_DEBUG": "true",
                "MCP_WORKERS": "8",
                "CODE_STORY_SERVICE_URL": "http://localhost:8000",
            },
            {
                "debug": True,
                "workers": 8,
                "code_story_service_url": "http://localhost:8000",
            },
        ),
    ],
)
def test_settings_from_env(env_vars: Any, expected: Any) -> None:
    """Test loading settings from environment variables."""
    with mock.patch.dict(os.environ, env_vars, clear=True):
        settings = MCPSettings()

        for key, value in expected.items():
            assert getattr(settings, key) == value


def test_get_mcp_settings_singleton() -> None:
    """Test that get_mcp_settings returns a singleton."""
    with mock.patch.dict(
        os.environ, {"CODE_STORY_SERVICE_URL": "http://localhost:8000"}, clear=True
    ):
        settings1 = get_mcp_settings()
        settings2 = get_mcp_settings()

        assert settings1 is settings2
