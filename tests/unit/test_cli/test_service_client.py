"""Unit tests for the ServiceClient class."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from codestory.cli.client import ServiceClient, ServiceError
from codestory.config import Settings


class TestServiceClient:
    """Tests for the ServiceClient class."""

    def test_init_with_default_values(self) -> None:
        """Test initialization with default values."""
        with patch("codestory.cli.client.service_client.get_settings") as mock_get_settings:
            # Create mock settings
            mock_settings = MagicMock()
            mock_service = MagicMock()
            mock_service.port = 8000
            mock_service.host = "localhost"  # Set host explicitly
            # Explicitly set api_key to None
            mock_service.api_key = None
            mock_settings.service = mock_service
            mock_get_settings.return_value = mock_settings

            # Create client
            client = ServiceClient()

            # Check client properties
            assert client.base_url == "http://localhost:8000/v1"
            assert client.api_key is None
            assert client.settings == mock_settings

            # Check headers
            headers = client._get_headers()
            assert "Content-Type" in headers
            assert "Accept" in headers
            assert "Authorization" not in headers

    def test_init_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        # Create client with custom values
        console = MagicMock()
        settings = MagicMock(spec=Settings)
        client = ServiceClient(
            base_url="http://example.com/api",
            api_key="test-api-key",
            console=console,
            settings=settings,
        )

        # Check client properties
        assert client.base_url == "http://example.com/api"
        assert client.api_key == "test-api-key"
        assert client.console == console
        assert client.settings == settings

        # Check headers
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-api-key"

    def test_api_key_from_settings(self) -> None:
        """Test getting API key from settings."""
        with patch("codestory.cli.client.service_client.get_settings") as mock_get_settings:
            # Create mock settings with API key as SecretStr
            mock_settings = MagicMock()
            mock_service = MagicMock()
            mock_service.port = 8000
            mock_service.api_key = SecretStr("settings-api-key")
            mock_settings.service = mock_service
            mock_get_settings.return_value = mock_settings

            # Create client
            client = ServiceClient()

            # Check API key
            assert client.api_key == "settings-api-key"

            # Check headers
            headers = client._get_headers()
            assert headers["Authorization"] == "Bearer settings-api-key"

    def test_check_service_health_success(self) -> None:
        """Test successful health check."""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "healthy"}

        # Mock client
        client = ServiceClient()
        client.client = MagicMock()
        client.client.get.return_value = mock_response

        # Check health
        result = client.check_service_health()

        # Verify result
        assert result["status"] == "healthy"
        # First call to /health with empty params dict
        client.client.get.assert_called_with("/health", params={})

    def test_check_service_health_error(self) -> None:
        """Test health check with error."""
        # Mock response
        client = ServiceClient()
        client.client = MagicMock()
        # Both endpoint calls will fail with HTTP error
        client.client.get.side_effect = httpx.HTTPError("Error")
        client.client.request.side_effect = httpx.HTTPError("Error")

        # Check health
        with pytest.raises(ServiceError, match="Health check failed:"):
            client.check_service_health()

    def test_start_ingestion(self) -> None:
        """Test starting ingestion."""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"job_id": "test-123"}

        # Mock client
        client = ServiceClient()
        client.client = MagicMock()
        client.client.post.return_value = mock_response

        # Start ingestion
        result = client.start_ingestion("/path/to/repo")

        # Verify result
        assert result == {"job_id": "test-123"}
        client.client.post.assert_called_once_with(
            "/ingest",
            json={
                "source_type": "local_path",
                "source": "/path/to/repo",
                "description": "CLI ingestion of repository: /path/to/repo",
            },
        )

    def test_execute_query(self) -> None:
        """Test executing a query."""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"records": []}

        # Mock client
        client = ServiceClient()
        client.client = MagicMock()
        client.client.post.return_value = mock_response

        # Execute query
        query = "MATCH (n) RETURN n"
        parameters = {"param1": "value1"}
        result = client.execute_query(query, parameters)

        # Verify result
        assert result == {"records": []}
        client.client.post.assert_called_once_with(
            "/query/cypher",
            json={"query": query, "parameters": parameters, "query_type": "read"},
        )

    def test_ask_question(self) -> None:
        """Test asking a question."""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"answer": "Test answer"}

        # Mock client
        client = ServiceClient()
        client.client = MagicMock()
        client.client.post.return_value = mock_response

        # Ask question
        result = client.ask_question("What is the meaning of life?")

        # Verify result
        assert result == {"answer": "Test answer"}
        client.client.post.assert_called_once_with(
            "/ask", json={"question": "What is the meaning of life?"}
        )

    def test_get_config(self) -> None:
        """Test getting configuration."""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"app_name": "code-story"}

        # Mock client
        client = ServiceClient()
        client.client = MagicMock()
        client.client.get.return_value = mock_response

        # Get config
        result = client.get_config(include_sensitive=True)

        # Verify result
        assert result == {"app_name": "code-story"}
        client.client.get.assert_called_once_with("/config", params={"include_sensitive": "true"})

    def test_update_config(self) -> None:
        """Test updating configuration."""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"app_name": "new-name"}

        # Mock client
        client = ServiceClient()
        client.client = MagicMock()
        client.client.patch.return_value = mock_response

        # Update config
        updates = {"app_name": "new-name"}
        result = client.update_config(updates)

        # Verify result
        assert result == {"app_name": "new-name"}
        client.client.patch.assert_called_once_with("/config", json=updates)

    def test_generate_visualization(self) -> None:
        """Test generating visualization."""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = "<html>Visualization</html>"

        # Mock client
        client = ServiceClient()
        client.client = MagicMock()
        client.client.get.return_value = mock_response

        # Set up mock client to return the same response for all the endpoints it tries
        client.console = MagicMock()  # Mock the console to suppress output

        # Generate visualization
        result = client.generate_visualization()

        # Verify result
        assert result == "<html>Visualization</html>"

        # Since the implementation tries multiple endpoints, we only verify that get was called at least once
        client.client.get.assert_called_with("/visualize")

        # Verify it was called only once (the first attempt succeeds)
        assert client.client.get.call_count == 1

    def test_open_ui(self) -> None:
        """Test opening the UI."""
        with patch("codestory.cli.client.service_client.webbrowser.open") as mock_open:
            # Create client with mock settings
            mock_settings = MagicMock()
            mock_service = MagicMock()
            mock_service.ui_url = "http://example.com/ui"
            mock_settings.service = mock_service

            client = ServiceClient(settings=mock_settings)

            # Open UI
            client.open_ui()

            # Verify browser was opened
            mock_open.assert_called_once_with("http://example.com/ui")

    def test_clear_database_success(self) -> None:
        """Test successful database clearing."""
        # Mock execute_query method
        client = ServiceClient()
        client.execute_query = MagicMock()
        client.execute_query.return_value = {"status": "success"}
        client.console = MagicMock()

        # Call clear_database with confirmation
        result = client.clear_database(confirm=True)

        # Verify the result
        assert result["status"] == "success"
        assert "message" in result
        assert "timestamp" in result

        # Verify execute_query was called twice
        assert client.execute_query.call_count == 2
        # First call should be to delete all nodes
        client.execute_query.assert_any_call(query="MATCH (n) DETACH DELETE n", query_type="write")
        # Second call should be to re-initialize schema
        client.execute_query.assert_any_call(
            query="CALL apoc.schema.assert({}, {})", query_type="write"
        )

    def test_clear_database_without_confirmation(self) -> None:
        """Test clearing database without confirmation."""
        # Create client
        client = ServiceClient()
        client.execute_query = MagicMock()

        # Call clear_database without confirmation
        with pytest.raises(ValueError, match="must be explicitly confirmed"):
            client.clear_database(confirm=False)

        # Verify execute_query was not called
        client.execute_query.assert_not_called()

    def test_clear_database_error(self) -> None:
        """Test database clearing with error."""
        # Create client
        client = ServiceClient()
        client.execute_query = MagicMock()
        client.execute_query.side_effect = ServiceError("Error message")
        client.console = MagicMock()

        # Call clear_database
        with pytest.raises(ServiceError, match="Failed to clear database"):
            client.clear_database(confirm=True)

    def test_clear_database_auth_error(self) -> None:
        """Test database clearing with authorization error."""
        # Create client
        client = ServiceClient()
        client.execute_query = MagicMock()
        client.execute_query.side_effect = ServiceError("Query execution failed: 403 Forbidden")
        client.console = MagicMock()

        # Call clear_database
        with pytest.raises(ServiceError, match="Administrative privileges required"):
            client.clear_database(confirm=True)
