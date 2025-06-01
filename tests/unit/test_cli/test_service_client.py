from typing import Any

'Unit tests for the ServiceClient class.'
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from codestory.cli.client import ServiceClient, ServiceError
from codestory.config import Settings


class TestServiceClient:
    """Tests for the ServiceClient class."""

    def test_init_with_default_values(self: Any) -> None:
        """Test initialization with default values."""
        with patch('codestory.cli.client.service_client.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_service = MagicMock()
            mock_service.port = 8000
            mock_service.host = 'localhost'
            mock_service.api_key = None
            mock_settings.service = mock_service
            mock_get_settings.return_value = mock_settings
            client = ServiceClient()
            assert client.base_url == 'http://localhost:8000/v1'
            assert client.api_key is None
            assert client.settings == mock_settings
            headers = client._get_headers()
            assert 'Content-Type' in headers
            assert 'Accept' in headers
            assert 'Authorization' not in headers

    def test_init_with_custom_values(self: Any) -> None:
        """Test initialization with custom values."""
        console = MagicMock()
        settings = MagicMock(spec=Settings)
        client = ServiceClient(base_url='http://example.com/api', api_key='test-api-key', console=console, settings=settings)
        assert client.base_url == 'http://example.com/api'
        assert client.api_key == 'test-api-key'
        assert client.console == console
        assert client.settings == settings
        headers = client._get_headers()
        assert headers['Authorization'] == 'Bearer test-api-key'

    def test_api_key_from_settings(self: Any) -> None:
        """Test getting API key from settings."""
        with patch('codestory.cli.client.service_client.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_service = MagicMock()
            mock_service.port = 8000
            mock_service.api_key = SecretStr('settings-api-key')
            mock_settings.service = mock_service
            mock_get_settings.return_value = mock_settings
            client = ServiceClient()
            assert client.api_key == 'settings-api-key'
            headers = client._get_headers()
            assert headers['Authorization'] == 'Bearer settings-api-key'

    def test_check_service_health_success(self: Any) -> None:
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'status': 'healthy'}
        client = ServiceClient()
        client.client = MagicMock()
        client.client.get.return_value = mock_response
        result = client.check_service_health()
        assert result['status'] == 'healthy'
        client.client.get.assert_called_with('/health', params={})

    def test_check_service_health_error(self: Any) -> None:
        """Test health check with error."""
        client = ServiceClient()
        client.client = MagicMock()
        client.client.get.side_effect = httpx.HTTPError('Error')
        client.client.request.side_effect = httpx.HTTPError('Error')
        with pytest.raises(ServiceError, match='Health check failed:'):
            client.check_service_health()

    def test_start_ingestion(self: Any) -> None:
        """Test starting ingestion."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'job_id': 'test-123'}
        client = ServiceClient()
        client.client = MagicMock()
        client.client.post.return_value = mock_response
        result = client.start_ingestion('/path/to/repo')
        assert result == {'job_id': 'test-123'}
        client.client.post.assert_called_once_with('/ingest', json={'source_type': 'local_path', 'source': '/path/to/repo', 'description': 'CLI ingestion of repository: /path/to/repo'})

    def test_execute_query(self: Any) -> None:
        """Test executing a query."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'records': []}
        client = ServiceClient()
        client.client = MagicMock()
        client.client.post.return_value = mock_response
        query = 'MATCH (n) RETURN n'
        parameters = {'param1': 'value1'}
        result = client.execute_query(query, parameters)
        assert result == {'records': []}
        client.client.post.assert_called_once_with('/query/cypher', json={'query': query, 'parameters': parameters, 'query_type': 'read'})

    def test_ask_question(self: Any) -> None:
        """Test asking a question."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'answer': 'Test answer'}
        client = ServiceClient()
        client.client = MagicMock()
        client.client.post.return_value = mock_response
        result = client.ask_question('What is the meaning of life?')
        assert result == {'answer': 'Test answer'}
        client.client.post.assert_called_once_with('/ask', json={'question': 'What is the meaning of life?'})

    def test_get_config(self: Any) -> None:
        """Test getting configuration."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'app_name': 'code-story'}
        client = ServiceClient()
        client.client = MagicMock()
        client.client.get.return_value = mock_response
        result = client.get_config(include_sensitive=True)
        assert result == {'app_name': 'code-story'}
        client.client.get.assert_called_once_with('/config', params={'include_sensitive': 'true'})

    def test_update_config(self: Any) -> None:
        """Test updating configuration."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'app_name': 'new-name'}
        client = ServiceClient()
        client.client = MagicMock()
        client.client.patch.return_value = mock_response
        updates = {'app_name': 'new-name'}
        result = client.update_config(updates)
        assert result == {'app_name': 'new-name'}
        client.client.patch.assert_called_once_with('/config', json=updates)

    def test_generate_visualization(self: Any) -> None:
        """Test generating visualization."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = '<html>Visualization</html>'
        client = ServiceClient()
        client.client = MagicMock()
        client.client.get.return_value = mock_response
        client.console = MagicMock()
        result = client.generate_visualization()
        assert result == '<html>Visualization</html>'
        client.client.get.assert_called_with('/visualize')
        assert client.client.get.call_count == 1

    def test_open_ui(self: Any) -> None:
        """Test opening the UI."""
        with patch('codestory.cli.client.service_client.webbrowser.open') as mock_open:
            mock_settings = MagicMock()
            mock_service = MagicMock()
            mock_service.ui_url = 'http://example.com/ui'
            mock_settings.service = mock_service
            client = ServiceClient(settings=mock_settings)
            client.open_ui()
            mock_open.assert_called_once_with('http://example.com/ui')

    def test_clear_database_success(self: Any) -> None:
        """Test successful database clearing."""
        client = ServiceClient()
        client.execute_query = MagicMock()
        client.execute_query.return_value = {'status': 'success'}
        client.console = MagicMock()
        result = client.clear_database(confirm=True)
        assert result['status'] == 'success'
        assert 'message' in result
        assert 'timestamp' in result
        assert client.execute_query.call_count == 2
        client.execute_query.assert_any_call(query='MATCH (n) DETACH DELETE n', query_type='write')
        client.execute_query.assert_any_call(query='CALL apoc.schema.assert({}, {})', query_type='write')

    def test_clear_database_without_confirmation(self: Any) -> None:
        """Test clearing database without confirmation."""
        client = ServiceClient()
        client.execute_query = MagicMock()
        with pytest.raises(ValueError, match='must be explicitly confirmed'):
            client.clear_database(confirm=False)
        client.execute_query.assert_not_called()

    def test_clear_database_error(self: Any) -> None:
        """Test database clearing with error."""
        client = ServiceClient()
        client.execute_query = MagicMock()
        client.execute_query.side_effect = ServiceError('Error message')
        client.console = MagicMock()
        with pytest.raises(ServiceError, match='Failed to clear database'):
            client.clear_database(confirm=True)

    def test_clear_database_auth_error(self: Any) -> None:
        """Test database clearing with authorization error."""
        client = ServiceClient()
        client.execute_query = MagicMock()
        client.execute_query.side_effect = ServiceError('Query execution failed: 403 Forbidden')
        client.console = MagicMock()
        with pytest.raises(ServiceError, match='Administrative privileges required'):
            client.clear_database(confirm=True)