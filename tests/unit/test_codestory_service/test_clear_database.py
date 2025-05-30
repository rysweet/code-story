from typing import Any
'Unit tests for database clear functionality.'
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
    service = MagicMock(spec=GraphService)
    service.clear_database = AsyncMock()
    service.clear_database.return_value = {'status': 'success', 'message': 'Database successfully cleared', 'timestamp': '2023-01-01T00:00:00Z'}
    return service

@pytest.fixture
def test_client(mock_graph_service: Any) -> None:
    """Create a test client with mocked dependencies."""
    app.dependency_overrides = {}

    async def mock_is_admin():
        return {'name': 'Admin User', 'roles': ['admin']}

    def mock_get_graph_service():
        return mock_graph_service
    from codestory_service.application.graph_service import get_graph_service
    from codestory_service.infrastructure.msal_validator import is_admin
    app.dependency_overrides[is_admin] = mock_is_admin
    app.dependency_overrides[get_graph_service] = mock_get_graph_service
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

def test_clear_database_success(test_client: Any, mock_graph_service: Any) -> None:
    """Test successful database clearing."""
    response = test_client.post('/v1/database/clear', json={'confirm': True, 'preserve_schema': True})
    assert response.status_code == 200
    assert response.json()['status'] == 'success'
    assert response.json()['message'] == 'Database successfully cleared'
    mock_graph_service.clear_database.assert_called_once()
    args, kwargs = mock_graph_service.clear_database.call_args
    request_arg = args[0]
    assert isinstance(request_arg, DatabaseClearRequest)
    assert request_arg.confirm is True
    assert request_arg.preserve_schema is True

def test_clear_database_without_confirmation(test_client: Any, mock_graph_service: Any) -> None:
    """Test clearing database without confirmation."""
    mock_graph_service.clear_database.side_effect = ValueError('Database clear operation must be explicitly confirmed')
    response = test_client.post('/v1/database/clear', json={'confirm': False, 'preserve_schema': True})
    assert response.status_code == 422
    assert 'confirm' in response.json()['detail'][0]['msg'].lower()

def test_clear_database_error(test_client: Any, mock_graph_service: Any) -> None:
    """Test database clearing with error."""
    mock_graph_service.clear_database.side_effect = HTTPException(status_code=500, detail='Error clearing database')
    response = test_client.post('/v1/database/clear', json={'confirm': True, 'preserve_schema': True})
    assert response.status_code == 500
    assert 'error clearing database' in response.json()['detail'].lower()