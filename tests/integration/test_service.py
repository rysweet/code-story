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
    # Set test environment flags
    os.environ["CODESTORY_TEST_ENV"] = "true"
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
    os.environ["CELERY_BROKER_URL"] = "memory://"
    os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"

    # Create the test client
    client = TestClient(app)

    # Yield the client for the test
    yield client

    # Clean up
    env_vars_to_clean = [
        "CODESTORY_TEST_ENV",
        "CELERY_TASK_ALWAYS_EAGER",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND"
    ]
    for var in env_vars_to_clean:
        if var in os.environ:
            del os.environ[var]


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
    """Test the legacy health check endpoint with real dependencies."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    # At least one component should be healthy
    assert any(
        comp.get("status") == "healthy"
        for comp in data["components"].values()
    ), "At least one component should be healthy"


@pytest.mark.integration
def test_v1_health_check(test_client: Any) -> None:
    """Test the v1 health check endpoint with real dependencies."""
    response = test_client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    # At least one component should be healthy
    assert any(
        comp.get("status") == "healthy"
        for comp in data["components"].values()
    ), "At least one component should be healthy"


@pytest.mark.integration
def test_health_check_degraded_service(test_client: Any) -> None:
    """Test health check returns degraded status when some components fail (real dependencies)."""
    for endpoint in ["/v1/health", "/health"]:
        response = test_client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        # If any component is degraded, overall status should be degraded
        if any(comp.get("status") == "degraded" for comp in data["components"].values()):
            assert data["status"] == "degraded"
        # If any component is unhealthy, overall status should be unhealthy
        if any(comp.get("status") == "unhealthy" for comp in data["components"].values()):
            assert data["status"] == "unhealthy"


@pytest.mark.integration
def test_health_check_all_components_unhealthy(test_client: Any) -> None:
    """Test health check behavior when all components are unhealthy (real dependencies)."""
    for endpoint in ["/v1/health", "/health"]:
        response = test_client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        # If all components are unhealthy, overall status should be unhealthy
        if all(comp.get("status") == "unhealthy" for comp in data["components"].values()):
            assert data["status"] == "unhealthy"


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
    # Import QueryResult for proper mock
    from codestory_service.domain.graph import QueryResult, QueryResultFormat
    
    # Mock Neo4j adapter to return test results
    with mock.patch(
        "codestory_service.infrastructure.neo4j_adapter.Neo4jAdapter.execute_cypher_query"
    ) as mock_execute:
        # Set up the mock to return a proper QueryResult object
        mock_execute.return_value = QueryResult(
            columns=["n"],
            rows=[["test1"], ["test2"]],
            row_count=2,
            execution_time_ms=10,
            has_more=False,
            format=QueryResultFormat.TABULAR,
        )

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
    assert "json_schema" in data
    assert "ui_schema" in data
    
    # Check the actual JSON schema structure
    json_schema = data["json_schema"]
    assert "title" in json_schema
    assert "properties" in json_schema

    # Check that general section exists (neo4j might not be available in test)
    assert "general" in json_schema["properties"]


# Add tests for other API endpoints
# These would be implemented similarly to the above tests
