"""Unit tests for database clear functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from codestory_service.application.graph_service import GraphService
from codestory_service.domain.graph import DatabaseClearRequest
from codestory_service.main import app


@pytest.fixture
def mock_graph_service():
    """Create a mock graph service."""
    # Set up the mock
    service = MagicMock(spec=GraphService)
    # Make clear_database an async mock
    service.clear_database = AsyncMock()
    service.clear_database.return_value = {
        "status": "success",
        "message": "Database successfully cleared",
        "timestamp": "2023-01-01T00:00:00Z",
    }
    return service


@pytest.fixture
def test_client(mock_graph_service):
    """Create a test client with mocked dependencies."""
    # Override the dependency
    app.dependency_overrides = {}

    # Mock the admin dependency to always succeed
    async def mock_is_admin():
        return {"name": "Admin User", "roles": ["admin"]}

    # Mock the graph service dependency
    def mock_get_graph_service():
        return mock_graph_service

    # Set up the dependency overrides
    from codestory_service.application.graph_service import get_graph_service
    from codestory_service.infrastructure.msal_validator import is_admin

    app.dependency_overrides[is_admin] = mock_is_admin
    app.dependency_overrides[get_graph_service] = mock_get_graph_service

    # Return the test client
    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides = {}


def test_clear_database_success(test_client, mock_graph_service):
    """Test successful database clearing."""
    # Set up test client
    response = test_client.post(
        "/v1/database/clear", json={"confirm": True, "preserve_schema": True}
    )

    # Check response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "Database successfully cleared"

    # Verify the service method was called
    mock_graph_service.clear_database.assert_called_once()
    # Get the call arguments
    args, kwargs = mock_graph_service.clear_database.call_args
    request_arg = args[0]
    assert isinstance(request_arg, DatabaseClearRequest)
    assert request_arg.confirm is True
    assert request_arg.preserve_schema is True


def test_clear_database_without_confirmation(test_client, mock_graph_service):
    """Test clearing database without confirmation."""
    # Set up service to raise error
    mock_graph_service.clear_database.side_effect = ValueError(
        "Database clear operation must be explicitly confirmed"
    )

    # Set up test client
    response = test_client.post(
        "/v1/database/clear", json={"confirm": False, "preserve_schema": True}
    )

    # Check response
    assert response.status_code == 422  # Validation error
    assert "confirm" in response.json()["detail"][0]["msg"].lower()


def test_clear_database_error(test_client, mock_graph_service):
    """Test database clearing with error."""
    # Set up service to raise error
    mock_graph_service.clear_database.side_effect = HTTPException(
        status_code=500, detail="Error clearing database"
    )

    # Set up test client
    response = test_client.post(
        "/v1/database/clear", json={"confirm": True, "preserve_schema": True}
    )

    # Check response
    assert response.status_code == 500
    assert "error clearing database" in response.json()["detail"].lower()
