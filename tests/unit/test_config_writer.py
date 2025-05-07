"""Tests for the configuration writer module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
import tomli

from src.codestory.config import (
    update_env,
    update_toml,
    update_config,
    get_config_value,
)
from src.codestory.config.exceptions import SettingNotFoundError


@pytest.fixture
def temp_env_file():
    """Fixture to create a temporary .env file."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write("NEO4J__URI=bolt://localhost:7687\n")
        f.write("NEO4J__USERNAME=neo4j\n")
        f.write("NEO4J__PASSWORD=test-password\n")
        f.write("REDIS__URI=redis://localhost:6379\n")
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


def test_update_env(temp_env_file):
    """Test updating values in a .env file."""
    # Update a value
    update_env("NEO4J__URI", "bolt://neo4j:7687", env_file=temp_env_file)
    
    # Read the file and check content
    with open(temp_env_file, "r") as f:
        content = f.read()
    
    assert 'NEO4J__URI="bolt://neo4j:7687"' in content
    assert 'NEO4J__USERNAME="neo4j"' in content
    
    # Update a value that doesn't exist yet
    update_env("NEW_SETTING", "new-value", env_file=temp_env_file)
    
    # Read the file and check content
    with open(temp_env_file, "r") as f:
        content = f.read()
    
    assert 'NEW_SETTING="new-value"' in content


def test_update_toml(temp_toml_file):
    """Test updating values in a .codestory.toml file."""
    # Update a value
    update_toml("neo4j", "uri", "bolt://neo4j:7687", toml_file=temp_toml_file)
    
    # Read the file and check content
    with open(temp_toml_file, "rb") as f:
        config = tomli.load(f)
    
    assert config["neo4j"]["uri"] == "bolt://neo4j:7687"
    assert config["neo4j"]["username"] == "neo4j"
    
    # Update a value that doesn't exist yet
    update_toml("service", "port", 9000, toml_file=temp_toml_file)
    
    # Read the file and check content
    with open(temp_toml_file, "rb") as f:
        config = tomli.load(f)
    
    assert "service" in config
    assert config["service"]["port"] == 9000
    
    # Update a nested value
    update_toml("ingestion.steps", "blarify.timeout", 300, toml_file=temp_toml_file)
    
    # Read the file and check content
    with open(temp_toml_file, "rb") as f:
        config = tomli.load(f)
    
    assert "ingestion" in config
    assert "steps" in config["ingestion"]
    assert "blarify" in config["ingestion"]["steps"]
    assert config["ingestion"]["steps"]["blarify"]["timeout"] == 300


def test_update_config_invalid_path():
    """Test updating a config value with an invalid path."""
    # Update a value with an invalid path
    with pytest.raises(ValueError):
        update_config("invalid", "value")
    
    # Update a value with an invalid section
    with pytest.raises(SettingNotFoundError):
        update_config("invalid.path", "value")
    
    # Update a value with an invalid key
    with pytest.raises(SettingNotFoundError):
        update_config("neo4j.invalid", "value")


@patch("src.codestory.config.writer.update_env")
def test_update_config_persist_env(mock_update_env):
    """Test updating a config value and persisting to .env."""
    # Update a value and persist to .env
    update_config("neo4j.uri", "bolt://neo4j:7687", persist_to="env")
    
    # Check that update_env was called with the correct arguments
    mock_update_env.assert_called_once_with("NEO4J__URI", "bolt://neo4j:7687")


@patch("src.codestory.config.writer.update_toml")
def test_update_config_persist_toml(mock_update_toml):
    """Test updating a config value and persisting to .toml."""
    # Update a value and persist to .toml
    update_config("neo4j.uri", "bolt://neo4j:7687", persist_to="toml")
    
    # Check that update_toml was called with the correct arguments
    mock_update_toml.assert_called_once_with("neo4j", "uri", "bolt://neo4j:7687")


@patch("src.codestory.config.writer.refresh_settings")
def test_update_config_refresh(mock_refresh_settings):
    """Test that update_config refreshes settings."""
    # Update a value
    update_config("neo4j.uri", "bolt://neo4j:7687")
    
    # Check that refresh_settings was called
    mock_refresh_settings.assert_called_once()