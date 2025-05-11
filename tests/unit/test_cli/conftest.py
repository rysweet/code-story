"""Test fixtures for CLI unit tests."""

import json
from typing import Dict, Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from rich.console import Console

from codestory.cli.client import ServiceClient


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    Creates a Click CLI test runner.
    
    Returns:
        Click CLI test runner.
    """
    return CliRunner()


@pytest.fixture
def mock_console() -> MagicMock:
    """
    Creates a mock Rich console.
    
    Returns:
        Mock Rich console.
    """
    console = MagicMock(spec=Console)
    return console


@pytest.fixture
def mock_service_client() -> Generator[MagicMock, None, None]:
    """
    Creates a mock service client and patches the ServiceClient class.
    
    Yields:
        Mock service client.
    """
    with patch("codestory.cli.client.service_client.ServiceClient") as mock_client_class:
        mock_client = MagicMock(spec=ServiceClient)
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_health_data() -> Dict[str, Any]:
    """
    Sample health check data.
    
    Returns:
        Sample health check data.
    """
    return {
        "service": {
            "status": "healthy",
            "message": "Service is running normally",
        },
        "neo4j": {
            "status": "healthy",
            "message": "Connected to Neo4j database",
        },
        "redis": {
            "status": "healthy",
            "message": "Connected to Redis",
        },
        "llm": {
            "status": "healthy",
            "message": "OpenAI API is accessible",
        },
    }


@pytest.fixture
def sample_ingestion_status() -> Dict[str, Any]:
    """
    Sample ingestion status data.
    
    Returns:
        Sample ingestion status data.
    """
    return {
        "job_id": "test-job-123",
        "repository_path": "/path/to/repo",
        "status": "running",
        "progress": 45.5,
        "created_at": "2023-05-01T12:34:56Z",
        "updated_at": "2023-05-01T12:45:00Z",
        "steps": [
            {
                "name": "filesystem",
                "status": "completed",
                "progress": 100.0,
                "message": "Filesystem step completed successfully",
            },
            {
                "name": "blarify",
                "status": "running",
                "progress": 60.0,
                "message": "Processing files...",
            },
            {
                "name": "summarizer",
                "status": "pending",
                "progress": 0.0,
                "message": "Waiting for dependencies",
            },
        ],
    }


@pytest.fixture
def sample_query_result() -> Dict[str, Any]:
    """
    Sample query result data.
    
    Returns:
        Sample query result data.
    """
    return {
        "records": [
            {
                "n": {"name": "Example", "type": "Class", "path": "/path/to/file.py"},
                "count": 42,
            },
            {
                "n": {"name": "AnotherExample", "type": "Function", "path": "/path/to/another.py"},
                "count": 10,
            },
        ],
    }


@pytest.fixture
def sample_config_data() -> Dict[str, Any]:
    """
    Sample configuration data.
    
    Returns:
        Sample configuration data.
    """
    return {
        "app_name": "code-story",
        "version": "0.1.0",
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password",
        },
        "service": {
            "host": "localhost",
            "port": 8000,
            "ui_url": "http://localhost:5173",
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "sk-12345",
        },
    }