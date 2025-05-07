"""Integration tests for the API service."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.codestory_service.main import app


@pytest.fixture
def client():
    """Create a TestClient instance for the API."""
    with patch.dict(os.environ, {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
        "REDIS_URI": "redis://localhost:6379",
        "OPENAI_API_KEY": "test-key",
    }, clear=True):
        with TestClient(app) as client:
            yield client


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "description" in data