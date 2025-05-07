"""Tests for the configuration module."""

import os
from unittest.mock import patch

import pytest

from src.codestory.config import Settings, get_settings


def test_settings_default_values():
    """Test default values for settings."""
    with patch.dict(os.environ, {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
        "REDIS_URI": "redis://localhost:6379",
        "OPENAI_API_KEY": "test-key",
    }, clear=True):
        settings = Settings()
        assert settings.project_name == "code-story"
        assert settings.version == "0.1.0"
        assert settings.neo4j.uri == "bolt://localhost:7687"
        assert settings.neo4j.user == "neo4j"
        assert settings.neo4j.password == "password"
        assert settings.redis.uri == "redis://localhost:6379"
        assert settings.openai.api_key == "test-key"
        assert settings.openai.model == "gpt-4o-2024-05-13"
        assert settings.service.host == "0.0.0.0"
        assert settings.service.port == 8000


def test_settings_override_from_env():
    """Test overriding settings from environment variables."""
    with patch.dict(os.environ, {
        "NEO4J_URI": "bolt://neo4j:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
        "REDIS_URI": "redis://redis:6379",
        "OPENAI_API_KEY": "test-key",
        "SERVICE_PORT": "9000",
        "OPENAI_MODEL": "gpt-4-turbo",
    }, clear=True):
        settings = Settings()
        assert settings.neo4j.uri == "bolt://neo4j:7687"
        assert settings.service.port == 9000
        assert settings.openai.model == "gpt-4-turbo"


def test_get_settings_cache():
    """Test that get_settings caches the result."""
    with patch.dict(os.environ, {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
        "REDIS_URI": "redis://localhost:6379",
        "OPENAI_API_KEY": "test-key",
    }, clear=True):
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2  # Same instance due to lru_cache