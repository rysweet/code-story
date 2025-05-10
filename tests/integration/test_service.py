"""Integration tests for the Code Story Service.

This module contains integration tests for the service, testing the API endpoints
against real components.
"""

import json
import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from codestory_service.main import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application.
    
    For proper integration testing, we minimize mocking and test actual interactions.
    However, we do need to mock external services like Neo4j and OpenAI that would
    require actual connections.
    """
    # Set up test environment variables
    os.environ["CODESTORY_SERVICE_DEV_MODE"] = "true"
    os.environ["CODESTORY_SERVICE_AUTH_ENABLED"] = "false"
    
    # For a true integration test, you would typically use actual components
    # that connect to test containers or test databases.
    # However, for simplicity, we'll use mocks for now.

    # Create a Neo4j connector with keys and other dictionary-like behaviors
    # that will work with the async code in the actual service
    class MockNeo4jConnector:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def keys(self):
            return []

        def get(self, key, default=None):
            return default

        async def close(self):
            pass

        def items(self):
            return []

        def __getitem__(self, key):
            return None

    # Create a mock health check function for components
    async def mock_healthy_check():
        return {"status": "healthy"}

    # Patch the necessary components
    with mock.patch("codestory_service.infrastructure.neo4j_adapter.Neo4jConnector", return_value=MockNeo4jConnector()):
        with mock.patch("codestory_service.api.health.Neo4jAdapter.check_health", return_value=mock_healthy_check()):
            with mock.patch("codestory_service.infrastructure.openai_adapter.OpenAIClient"):
                with mock.patch("codestory_service.api.health.OpenAIAdapter.check_health", return_value=mock_healthy_check()):
                    with mock.patch("codestory_service.infrastructure.celery_adapter.CeleryAdapter"):
                        with mock.patch("codestory_service.api.health.CeleryAdapter.check_health", return_value=mock_healthy_check()):
                            # Bypass authorization by returning a decorator that simply returns the user
                            with mock.patch("codestory_service.api.ingest.require_role", return_value=lambda roles: lambda func: func):
                                with mock.patch("codestory_service.api.graph.require_role", return_value=lambda roles: lambda func: func):
                                    with mock.patch("codestory_service.api.config.require_role", return_value=lambda roles: lambda func: func):
                                        # Create the app with these mocked dependencies
                                        app = create_app()

                                        # Return the test client
                                        test_client = TestClient(app)
                                        yield test_client

                                        # Clean up environment after tests
                                        os.environ.pop("CODESTORY_SERVICE_DEV_MODE", None)
                                        os.environ.pop("CODESTORY_SERVICE_AUTH_ENABLED", None)


def test_root_endpoint(client):
    """Test the root endpoint returns basic service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "description" in data


def test_legacy_health_check(client):
    """Test the legacy health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_v1_health_check(client):
    """Test the v1 health check endpoint."""
    # Create async mock functions for each component's health check
    async def mock_health_check(*args, **kwargs):
        return {"status": "healthy"}

    # Mock all the adapter health checks with awaitable functions
    with mock.patch("codestory_service.infrastructure.neo4j_adapter.Neo4jAdapter.check_health",
                   side_effect=mock_health_check):
        with mock.patch("codestory_service.infrastructure.openai_adapter.OpenAIAdapter.check_health",
                       side_effect=mock_health_check):
            with mock.patch("codestory_service.infrastructure.celery_adapter.CeleryAdapter.check_health",
                           side_effect=mock_health_check):

                response = client.get("/v1/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert "components" in data
                assert "neo4j" in data["components"]
                assert "celery" in data["components"]
                assert "openai" in data["components"]


def test_openapi_docs(client):
    """Test that OpenAPI docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert "/v1/health" in data["paths"]
    assert "/v1/ingest" in data["paths"]


def test_ingest_api(client):
    """Test the ingestion API endpoints."""
    # Create an async mock function for the start_ingestion method
    async def mock_start_ingestion(*args, **kwargs):
        from codestory_service.domain.ingestion import IngestionStarted, JobStatus
        return IngestionStarted(
            job_id="test-job-123",
            status=JobStatus.PENDING,
            source="/path/to/repo",
            steps=["filesystem", "summarizer", "docgrapher"],
            message="Job submitted",
            eta=1620000000
        )

    # Mock the ingestion service to return test data
    with mock.patch("codestory_service.application.ingestion_service.IngestionService.start_ingestion",
                   side_effect=mock_start_ingestion):

        # Test POST /v1/ingest
        response = client.post(
            "/v1/ingest",
            json={
                "source_type": "local_path",
                "source": "/path/to/repo"
            }
        )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == "test-job-123"
        assert data["status"] == "pending"


def test_query_api(client):
    """Test the query API endpoints."""
    # Create an async mock function for execute_cypher_query
    async def mock_execute_query(*args, **kwargs):
        from codestory_service.domain.graph import QueryResult
        return QueryResult(
            query_id="query-123",
            columns=["name", "value"],
            rows=[["test", 123]],
            row_count=1,
            execution_time_ms=50,
            has_more=False
        )

    # Mock the graph service to return test data
    with mock.patch("codestory_service.application.graph_service.GraphService.execute_cypher_query",
                   side_effect=mock_execute_query):

        # Test POST /v1/query/cypher
        response = client.post(
            "/v1/query/cypher",
            json={
                "query": "MATCH (n) RETURN n.name, n.value",
                "parameters": {},
                "query_type": "read"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["columns"] == ["name", "value"]
        assert data["rows"] == [["test", 123]]
        assert data["row_count"] == 1


def test_auth_api(client):
    """Test the authentication API endpoints."""
    # Mock the auth service to return test data
    with mock.patch("codestory_service.api.auth.AuthService.login") as mock_login:
        from codestory_service.domain.auth import TokenResponse
        mock_login.return_value = TokenResponse(
            access_token="test.jwt.token",
            token_type="Bearer",
            expires_in=3600,
            scope="api"
        )
        
        # Test POST /v1/auth/login
        response = client.post(
            "/v1/auth/login",
            json={
                "username": "testuser",
                "password": "password"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test.jwt.token"
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 3600


def test_config_api(client):
    """Test the configuration API endpoints."""
    # Create an async mock function for get_config_dump
    async def mock_get_config_dump(*args, **kwargs):
        from codestory_service.domain.config import (
            ConfigDump, ConfigGroup, ConfigItem, ConfigMetadata,
            ConfigSection, ConfigValueType, ConfigPermission, ConfigSource
        )

        # Create a sample config dump
        groups = {
            ConfigSection.GENERAL: ConfigGroup(
                section=ConfigSection.GENERAL,
                items={
                    "debug": ConfigItem(
                        value=True,
                        metadata=ConfigMetadata(
                            section=ConfigSection.GENERAL,
                            key="debug",
                            type=ConfigValueType.BOOLEAN,
                            description="Debug mode",
                            source=ConfigSource.CONFIG_FILE,
                            permission=ConfigPermission.READ_WRITE
                        )
                    )
                }
            )
        }

        return ConfigDump(
            groups=groups,
            version="1.0.0",
            last_updated="2025-05-09T10:00:00Z"
        )

    # Mock the config service to return test data
    with mock.patch("codestory_service.application.config_service.ConfigService.get_config_dump",
                   side_effect=mock_get_config_dump):

        # Test GET /v1/config
        response = client.get("/v1/config")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.0"
        assert "GENERAL" in data["groups"]
        assert "debug" in data["groups"]["GENERAL"]["items"]