from typing import Any
"""Integration tests for the Code Story Service.

These tests verify the service's API endpoints behave correctly
when interacting with real or mocked dependencies.
"""

import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from codestory_service.main import app


@pytest.fixture
def test_client() -> None:
    """Create a test client for the application."""
    # Set test environment flag
    os.environ["CODESTORY_TEST_ENV"] = "true"

    # Create the test client
    client = TestClient(app)

    # Yield the client for the test
    yield client

    # Clean up
    if "CODESTORY_TEST_ENV" in os.environ:
        del os.environ["CODESTORY_TEST_ENV"]


@pytest.mark.integration
def test_root_endpoint(test_client: Any) -> None:
    """Test the root endpoint for application metadata."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "description" in data


@pytest.mark.integration
def test_legacy_health_check(test_client: Any) -> None:
    """Test the legacy health check endpoint."""
    # Mock needed components to ensure consistent test results
    with mock.patch(
        "codestory_service.infrastructure.neo4j_adapter.Neo4jAdapter.check_health"
    ) as mock_neo4j_health:
        mock_neo4j_health.return_value = {
            "status": "healthy",
            "details": {"database": "testdb"},
        }

        with mock.patch(
            "codestory_service.infrastructure.openai_adapter.OpenAIAdapter.check_health"
        ) as mock_openai_health:
            mock_openai_health.return_value = {
                "status": "healthy",
                "details": {"models": ["text-embedding-ada-002", "gpt-4"]},
            }

            # Also mock Celery adapter
            with mock.patch(
                "codestory_service.infrastructure.celery_adapter.CeleryAdapter.check_health"
            ) as mock_celery_health:
                mock_celery_health.return_value = {
                    "status": "healthy",
                    "details": {"active_workers": 1, "registered_tasks": 5},
                }

                # Mock Redis client class with a context manager
                with mock.patch("redis.asyncio.Redis", autospec=True) as MockRedis:
                    # Create a mock instance
                    mock_redis_instance = mock.MagicMock()

                    # Configure the async methods
                    ping_mock = mock.AsyncMock()
                    ping_mock.return_value = True
                    mock_redis_instance.ping = ping_mock

                    info_mock = mock.AsyncMock()
                    info_mock.return_value = {
                        "redis_version": "6.2.0",
                        "used_memory_human": "1.5M",
                    }
                    mock_redis_instance.info = info_mock

                    close_mock = mock.AsyncMock()
                    mock_redis_instance.close = close_mock

                    # Make the constructor return our mock instance
                    MockRedis.return_value = mock_redis_instance

                    response = test_client.get("/health")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "healthy"


@pytest.mark.integration
def test_v1_health_check(test_client: Any) -> None:
    """Test the v1 health check endpoint with all services mocked.

    This test verifies that the health check endpoint successfully checks
    the health of all components by mocking them to ensure consistent
    test results without dependencies on external services.
    """
    # Mock all required services for a comprehensive health check
    with mock.patch(
        "codestory_service.infrastructure.neo4j_adapter.Neo4jAdapter.check_health"
    ) as mock_neo4j_health:
        # Provide a successful health check response for Neo4j
        mock_neo4j_health.return_value = {
            "status": "healthy",
            "details": {
                "database": "testdb",
                "version": "5.0",
            },
        }

        with mock.patch(
            "codestory_service.infrastructure.celery_adapter.CeleryAdapter.check_health"
        ) as mock_celery_health:
            # Provide a successful health check response for Celery
            mock_celery_health.return_value = {
                "status": "healthy",
                "details": {"active_workers": 1, "registered_tasks": 5},
            }

            with mock.patch(
                "codestory_service.infrastructure.openai_adapter.OpenAIAdapter.check_health"
            ) as mock_openai_health:
                # Provide a successful health check response for OpenAI
                mock_openai_health.return_value = {
                    "status": "healthy",
                    "details": {
                        "models": ["text-embedding-ada-002", "gpt-4"],
                        "api_version": "2023-05-15",
                    },
                }

                # Mock Redis client
                with mock.patch("redis.asyncio.Redis", autospec=True) as MockRedis:
                    # Create a mock instance
                    mock_redis_instance = mock.MagicMock()

                    # Configure the async methods
                    mock_redis_instance.ping = mock.AsyncMock(return_value=True)
                    mock_redis_instance.info = mock.AsyncMock(
                        return_value={
                            "redis_version": "6.2.0",
                            "used_memory_human": "1.5M",
                        }
                    )
                    mock_redis_instance.close = mock.AsyncMock()

                    # Make the constructor return our mock instance
                    MockRedis.return_value = mock_redis_instance

                    # Now test the health check with all components mocked
                    response = test_client.get("/v1/health")
                    assert response.status_code == 200
                    data = response.json()

                    # Overall status should be healthy
                    assert data["status"] == "healthy"
                    assert "components" in data

                    # All individual components should be healthy
                    for component_name in ["neo4j", "celery", "openai", "redis"]:
                        assert component_name in data["components"]
                        assert data["components"][component_name]["status"] == "healthy"

                    # Verify our mocks were called
                    mock_neo4j_health.assert_called_once()
                    mock_celery_health.assert_called_once()
                    mock_openai_health.assert_called_once()


@pytest.mark.integration
def test_health_check_degraded_service(test_client: Any) -> None:
    """Test health check returns degraded status when some components fail.

    This test verifies that:
    1. The service returns HTTP 200 even when components are degraded
    2. The overall status properly reflects component failures
    3. Individual component statuses are reported correctly
    """
    # Mock Neo4j as healthy
    with mock.patch(
        "codestory_service.infrastructure.neo4j_adapter.Neo4jAdapter.check_health"
    ) as mock_neo4j_health:
        mock_neo4j_health.return_value = {
            "status": "healthy",
            "details": {"database": "testdb"},
        }

        # Mock Celery as degraded
        with mock.patch(
            "codestory_service.infrastructure.celery_adapter.CeleryAdapter.check_health"
        ) as mock_celery_health:
            mock_celery_health.return_value = {
                "status": "degraded",
                "details": {
                    "active_workers": 1,
                    "expected_workers": 2,
                    "message": "Fewer workers than expected",
                },
            }

            # Mock OpenAI as unhealthy
            with mock.patch(
                "codestory_service.infrastructure.openai_adapter.OpenAIAdapter.check_health"
            ) as mock_openai_health:
                mock_openai_health.return_value = {
                    "status": "unhealthy",
                    "details": {
                        "error": "API authentication failed",
                        "message": "Service running in limited mode",
                    },
                }

                # Mock Redis client
                with mock.patch("redis.asyncio.Redis", autospec=True) as MockRedis:
                    # Create a mock instance with healthy response
                    mock_redis_instance = mock.MagicMock()
                    mock_redis_instance.ping = mock.AsyncMock(return_value=True)
                    mock_redis_instance.info = mock.AsyncMock(
                        return_value={
                            "redis_version": "6.2.0",
                            "used_memory_human": "1.5M",
                        }
                    )
                    mock_redis_instance.close = mock.AsyncMock()
                    MockRedis.return_value = mock_redis_instance

                    # Test both endpoints for consistent behavior
                    endpoints = ["/v1/health", "/health"]

                    for endpoint in endpoints:
                        # Test the health check endpoint
                        response = test_client.get(endpoint)

                        # Should still return 200 OK even though components are failing
                        assert response.status_code == 200
                        data = response.json()

                        # Overall status should be degraded
                        assert data["status"] == "degraded"
                        assert "components" in data

                        # Check individual component statuses
                        if "neo4j" in data["components"]:
                            assert data["components"]["neo4j"]["status"] == "healthy"
                        if "celery" in data["components"]:
                            assert data["components"]["celery"]["status"] == "degraded"
                        if "openai" in data["components"]:
                            assert data["components"]["openai"]["status"] == "unhealthy"
                        if "redis" in data["components"]:
                            assert data["components"]["redis"]["status"] == "healthy"


@pytest.mark.integration
def test_health_check_all_components_unhealthy(test_client: Any) -> None:
    """Test health check behavior when all components are unhealthy.

    This test verifies that:
    1. The service returns HTTP 200 even when all components are unhealthy
    2. The overall status is marked as unhealthy
    3. Individual component statuses show as unhealthy
    """
    # Mock all components as unhealthy
    with mock.patch(
        "codestory_service.infrastructure.neo4j_adapter.Neo4jAdapter.check_health"
    ) as mock_neo4j_health:
        mock_neo4j_health.return_value = {
            "status": "unhealthy",
            "details": {"error": "Database connection failed"},
        }

        with mock.patch(
            "codestory_service.infrastructure.celery_adapter.CeleryAdapter.check_health"
        ) as mock_celery_health:
            mock_celery_health.return_value = {
                "status": "unhealthy",
                "details": {"error": "No workers available"},
            }

            with mock.patch(
                "codestory_service.infrastructure.openai_adapter.OpenAIAdapter.check_health"
            ) as mock_openai_health:
                mock_openai_health.return_value = {
                    "status": "unhealthy",
                    "details": {"error": "API authentication failed"},
                }

                # Mock Redis with unhealthy response (fails to connect)
                with mock.patch("redis.asyncio.Redis", autospec=True) as MockRedis:
                    # Create a mock instance that raises exception on ping
                    mock_redis_instance = mock.MagicMock()
                    mock_redis_instance.ping = mock.AsyncMock(
                        side_effect=Exception("Connection refused")
                    )
                    MockRedis.return_value = mock_redis_instance

                    # Test both endpoints
                    for endpoint in ["/v1/health", "/health"]:
                        response = test_client.get(endpoint)

                        # Should still return 200 OK
                        assert response.status_code == 200
                        data = response.json()

                        # Overall status should be unhealthy
                        assert data["status"] == "unhealthy"
                        assert "components" in data

                        # Check all components show as unhealthy
                        if "neo4j" in data["components"]:
                            assert data["components"]["neo4j"]["status"] == "unhealthy"
                        if "celery" in data["components"]:
                            assert data["components"]["celery"]["status"] == "unhealthy"
                        if "openai" in data["components"]:
                            assert data["components"]["openai"]["status"] == "unhealthy"
                        if "redis" in data["components"]:
                            assert data["components"]["redis"]["status"] == "unhealthy"


@pytest.mark.integration
def test_openapi_docs(test_client: Any) -> None:
    """Test that OpenAPI docs are available."""
    response = test_client.get("/docs")
    assert response.status_code == 200

    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert "/v1/health" in data["paths"]
    assert "/v1/ingest" in data["paths"]


@pytest.mark.integration
def test_query_api(test_client: Any) -> None:
    """Test query API endpoint."""
    # Mock Neo4j adapter to return test results
    with mock.patch(
        "codestory_service.infrastructure.neo4j_adapter.Neo4jAdapter.execute_cypher_query"
    ) as mock_execute:
        # Set up the mock to return test results
        mock_execute.return_value = {
            "columns": ["n"],
            "rows": [["test1"], ["test2"]],
            "row_count": 2,
            "execution_time_ms": 10,
            "has_more": False,
            "format": "tabular",
        }

        # Test the cypher query endpoint
        response = test_client.post(
            "/v1/query/cypher",
            json={
                "query": "MATCH (n) RETURN n LIMIT 10",
                "parameters": {"limit": 10},
                "query_type": "read",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["row_count"] == 2
        assert len(data["rows"]) == 2
        assert data["columns"] == ["n"]


@pytest.mark.integration
def test_config_api_minimal(test_client: Any) -> None:
    """Test configuration API with minimal interaction."""
    # Get configuration schema
    response = test_client.get("/v1/config/schema")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "properties" in data

    # Check that neo4j section exists
    assert "neo4j" in data["properties"]


# Add tests for other API endpoints
# These would be implemented similarly to the above tests
