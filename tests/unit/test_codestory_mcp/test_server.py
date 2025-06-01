from typing import Any

'Unit tests for the MCP Adapter server.'
import asyncio
from unittest import mock

import pytest
from fastapi import FastAPI, HTTPException, status

from codestory_mcp.server import create_app, get_current_user, tool_executor
from codestory_mcp.tools.base import BaseTool, ToolError


@pytest.fixture
def mock_settings() -> None:
    """Create a mock settings object."""
    with mock.patch('codestory_mcp.server.get_mcp_settings') as mock_get_settings:
        settings = mock.Mock()
        settings.auth_enabled = True
        settings.azure_tenant_id = 'test-tenant'
        settings.api_audience = 'test-audience'
        settings.cors_origins = ['*']
        settings.prometheus_metrics_path = '/metrics'
        settings.openapi_url = '/openapi.json'
        settings.docs_url = '/docs'
        settings.redoc_url = '/redoc'
        mock_get_settings.return_value = settings
        yield settings

@pytest.fixture
def mock_metrics() -> None:
    """Create a mock metrics object."""
    with mock.patch('codestory_mcp.server.get_metrics') as mock_get_metrics:
        metrics = mock.Mock()
        mock_get_metrics.return_value = metrics
        yield metrics

@pytest.fixture
def mock_entra_validator() -> None:
    """Create a mock EntraValidator."""
    with mock.patch('codestory_mcp.server.EntraValidator') as mock_validator_cls:
        validator = mock.Mock()
        mock_validator_cls.return_value = validator
        yield validator

@pytest.fixture
def mock_tool() -> None:
    """Create a mock tool."""
    with mock.patch('codestory_mcp.server.get_tool') as mock_get_tool:
        tool_cls = mock.Mock(spec=BaseTool)
        tool = mock.Mock()
        tool_cls.return_value = tool
        mock_get_tool.return_value = tool_cls
        yield tool

@pytest.mark.asyncio
async def test_get_current_user_with_auth_disabled(mock_settings: Any, mock_metrics: Any) -> None:
    """Test get_current_user with authentication disabled."""
    mock_settings.auth_enabled = False
    request = mock.Mock()
    user = await get_current_user(request)
    assert user['sub'] == 'anonymous'
    assert user['name'] == 'Anonymous User'
    assert user['scopes'] == ['*']
    assert not mock_metrics.record_auth_attempt.called

@pytest.mark.asyncio
async def test_get_current_user_without_auth_header(mock_settings: Any, mock_metrics: Any) -> None:
    """Test get_current_user without auth header."""
    mock_settings.auth_enabled = True
    request = mock.Mock()
    request.headers = {}
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(request)
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert 'Missing or invalid authentication token' in excinfo.value.detail
    mock_metrics.record_auth_attempt.assert_called_once_with('error')

@pytest.mark.asyncio
async def test_get_current_user_with_valid_token(mock_settings: Any, mock_metrics: Any, mock_entra_validator: Any) -> None:
    """Test get_current_user with valid token."""
    mock_settings.auth_enabled = True
    request = mock.Mock()
    request.headers = {'Authorization': 'Bearer test-token'}
    future = asyncio.Future()
    future.set_result({'sub': 'test-user', 'name': 'Test User', 'scopes': ['code-story.read']})
    mock_entra_validator.validate_token.return_value = future
    user = await get_current_user(request)
    assert user['sub'] == 'test-user'
    assert user['name'] == 'Test User'
    assert user['scopes'] == ['code-story.read']
    mock_metrics.record_auth_attempt.assert_called_once_with('success')

@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token(mock_settings: Any, mock_metrics: Any, mock_entra_validator: Any) -> None:
    """Test get_current_user with invalid token."""
    mock_settings.auth_enabled = True
    request = mock.Mock()
    request.headers = {'Authorization': 'Bearer invalid-token'}
    future = asyncio.Future()
    future.set_exception(Exception('Invalid token'))
    mock_entra_validator.validate_token.return_value = future
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(request)
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert 'Invalid authentication token' in excinfo.value.detail
    mock_metrics.record_auth_attempt.assert_called_once_with('error')

@pytest.mark.asyncio
async def test_tool_executor_success(mock_metrics: Any, mock_tool: Any) -> None:
    """Test tool executor with successful execution."""
    executor = tool_executor(lambda tool_name, params, user: None)
    future = asyncio.Future()
    future.set_result({'result': 'success'})
    mock_tool.return_value = future
    result = await executor('testTool', {'param': 'value'}, {'sub': 'test-user'})
    mock_tool.assert_called_once()
    mock_tool.validate_parameters.assert_called_once_with({'param': 'value'})
    mock_metrics.record_tool_call.assert_called_once()
    assert mock_metrics.record_tool_call.call_args[0][0] == 'testTool'
    assert mock_metrics.record_tool_call.call_args[0][1] == 'success'
    assert result == {'result': 'success'}

@pytest.mark.asyncio
async def test_tool_executor_tool_not_found(mock_metrics: Any, mock_tool: Any) -> None:
    """Test tool executor with tool not found."""
    executor = tool_executor(lambda tool_name, params, user: None)
    with mock.patch('codestory_mcp.server.get_tool', side_effect=KeyError('Tool not found')):
        with pytest.raises(HTTPException) as excinfo:
            await executor('nonexistentTool', {'param': 'value'}, {'sub': 'test-user'})
        assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND
        assert 'Tool not found' in excinfo.value.detail
        mock_metrics.record_tool_call.assert_called_once()
        assert mock_metrics.record_tool_call.call_args[0][0] == 'nonexistentTool'
        assert mock_metrics.record_tool_call.call_args[0][1] == 'error'

@pytest.mark.asyncio
async def test_tool_executor_tool_error(mock_metrics: Any, mock_tool: Any) -> None:
    """Test tool executor with tool error."""
    executor = tool_executor(lambda tool_name, params, user: None)
    future = asyncio.Future()
    future.set_exception(ToolError('Tool execution failed', status_code=status.HTTP_400_BAD_REQUEST))
    mock_tool.return_value = future
    with pytest.raises(HTTPException) as excinfo:
        await executor('testTool', {'param': 'value'}, {'sub': 'test-user'})
    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Tool execution failed' in excinfo.value.detail
    mock_metrics.record_tool_call.assert_called_once()
    assert mock_metrics.record_tool_call.call_args[0][0] == 'testTool'
    assert mock_metrics.record_tool_call.call_args[0][1] == 'error'

@pytest.mark.asyncio
async def test_tool_executor_validation_error(mock_metrics: Any, mock_tool: Any) -> None:
    """Test tool executor with validation error."""
    executor = tool_executor(lambda tool_name, params, user: None)
    mock_tool.validate_parameters.side_effect = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid parameters')
    with pytest.raises(HTTPException) as excinfo:
        await executor('testTool', {'param': 'value'}, {'sub': 'test-user'})
    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Invalid parameters' in excinfo.value.detail
    mock_metrics.record_tool_call.assert_called_once()
    assert mock_metrics.record_tool_call.call_args[0][0] == 'testTool'
    assert mock_metrics.record_tool_call.call_args[0][1] == 'error'

@pytest.mark.asyncio
async def test_tool_executor_unexpected_error(mock_metrics: Any, mock_tool: Any) -> None:
    """Test tool executor with unexpected error."""
    executor = tool_executor(lambda tool_name, params, user: None)
    future = asyncio.Future()
    future.set_exception(ValueError('Unexpected error'))
    mock_tool.return_value = future
    with pytest.raises(HTTPException) as excinfo:
        await executor('testTool', {'param': 'value'}, {'sub': 'test-user'})
    assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert 'Tool execution error' in excinfo.value.detail
    mock_metrics.record_tool_call.assert_called_once()
    assert mock_metrics.record_tool_call.call_args[0][0] == 'testTool'
    assert mock_metrics.record_tool_call.call_args[0][1] == 'error'

def test_create_app(mock_settings: Any) -> None:
    """Test app creation."""
    with mock.patch('codestory_mcp.server.CORSMiddleware'), mock.patch('codestory_mcp.server.make_asgi_app'):
        app = create_app()
        assert isinstance(app, FastAPI)
        assert app.title == 'Code Story MCP'
        assert app.openapi_url == mock_settings.openapi_url
        assert app.docs_url == mock_settings.docs_url
        assert app.redoc_url == mock_settings.redoc_url
        route_paths = [route.path for route in app.routes]
        assert '/v1/tools/{tool_name}' in route_paths
        assert '/v1/tools' in route_paths
        assert '/v1/health' in route_paths