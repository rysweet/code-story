"""Integration tests for the MCP Adapter."""

import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from codestory_mcp.server import create_app
from codestory_mcp.tools.search_graph import SearchGraphTool
from codestory_mcp.tools.summarize_node import SummarizeNodeTool
from codestory_mcp.tools.path_to import PathToTool
from codestory_mcp.tools.similar_code import SimilarCodeTool
from codestory_mcp.tools import register_tool


@pytest.fixture
def client():
    """Create a test client for the MCP server."""
    # Set environment variables for testing
    os.environ["AUTH_ENABLED"] = "false"
    os.environ["CODE_STORY_SERVICE_URL"] = "http://localhost:8000"

    # Override get_mcp_settings to avoid validation error
    with mock.patch("codestory_mcp.server.get_mcp_settings") as mock_get_settings:
        mock_settings = mock.MagicMock()
        mock_settings.code_story_service_url = "http://localhost:8000"
        mock_settings.auth_enabled = False
        mock_settings.port = 8001
        mock_settings.host = "0.0.0.0"
        mock_settings.cors_origins = ["*"]
        mock_settings.openapi_url = "/openapi.json"
        mock_settings.docs_url = "/docs"
        mock_settings.redoc_url = "/redoc"
        mock_settings.prometheus_metrics_path = "/metrics"
        mock_get_settings.return_value = mock_settings

    # Create app with mocked adapters
    with mock.patch(
        "codestory_mcp.adapters.graph_service.GraphServiceAdapter"
    ), mock.patch("codestory_mcp.adapters.openai_service.OpenAIServiceAdapter"):
        # Register tools manually for testing
        register_tool(SearchGraphTool)
        register_tool(SummarizeNodeTool)
        register_tool(PathToTool)
        register_tool(SimilarCodeTool)

        app = create_app()
        yield TestClient(app)

    # Clean up environment
    os.environ.pop("AUTH_ENABLED", None)
    os.environ.pop("CODE_STORY_SERVICE_URL", None)


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_tools(client):
    """Test getting available tools."""
    response = client.get("/v1/tools")

    assert response.status_code == 200
    assert "tools" in response.json()

    tools = response.json()["tools"]
    tool_names = [tool["name"] for tool in tools]

    assert "searchGraph" in tool_names
    assert "summarizeNode" in tool_names
    assert "pathTo" in tool_names
    assert "similarCode" in tool_names


def test_execute_search_graph_tool(client):
    """Test executing the searchGraph tool."""
    # Mock the GraphServiceAdapter search method and serializer
    with mock.patch(
        "codestory_mcp.tools.search_graph.get_graph_service"
    ) as mock_get_service, mock.patch(
        "codestory_mcp.tools.search_graph.NodeSerializer"
    ) as mock_serializer:
        service = mock.AsyncMock()
        mock_get_service.return_value = service

        # Mock search results
        mock_node = mock.Mock()
        mock_node.id = "node-123"
        mock_node.labels = ["Class"]
        mock_node.properties = {"name": "TestClass", "path": "/path/to/test.py"}
        mock_node.get = mock.Mock(
            side_effect=lambda k, d=None: mock_node.properties.get(k, d)
        )
        mock_node.items = mock.Mock(return_value=mock_node.properties.items())

        # Set up async mock correctly
        service.search.return_value = [(mock_node, 0.95)]

        # Mock serializer response
        mock_serializer.to_mcp_result.return_value = {
            "matches": [
                {
                    "id": "node-123",
                    "type": "Class",
                    "name": "TestClass",
                    "path": "/path/to/test.py",
                    "score": 0.95,
                    "properties": {},
                }
            ]
        }

        # Execute tool
        response = client.post(
            "/v1/tools/searchGraph",
            json={"query": "test query", "node_types": ["Class"], "limit": 5},
        )

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert "matches" in data
        assert len(data["matches"]) == 1
        assert data["matches"][0]["id"] == "node-123"
        assert data["matches"][0]["type"] == "Class"
        assert data["matches"][0]["name"] == "TestClass"
        assert data["matches"][0]["score"] == 0.95

        # Verify service call
        service.search.assert_called_once_with(
            query="test query", node_types=["Class"], limit=5
        )


def test_execute_summarize_node_tool(client):
    """Test executing the summarizeNode tool."""
    # Mock the GraphServiceAdapter and OpenAIServiceAdapter
    with mock.patch(
        "codestory_mcp.tools.summarize_node.get_graph_service"
    ) as mock_get_graph_service, mock.patch(
        "codestory_mcp.tools.summarize_node.get_openai_service"
    ) as mock_get_openai_service:
        graph_service = mock.AsyncMock()
        openai_service = mock.AsyncMock()
        mock_get_graph_service.return_value = graph_service
        mock_get_openai_service.return_value = openai_service

        # Mock node
        mock_node = mock.Mock()
        mock_node.id = "node-123"
        mock_node.labels = ["Class"]
        mock_node.properties = {
            "name": "TestClass",
            "path": "/path/to/test.py",
            "content": "class TestClass:\n    pass",
        }
        mock_node.get = mock.Mock(
            side_effect=lambda k, d=None: mock_node.properties.get(k, d)
        )

        graph_service.find_node.return_value = mock_node

        # Mock summary
        openai_service.generate_code_summary.return_value = "A simple test class."

        # Execute tool
        response = client.post(
            "/v1/tools/summarizeNode",
            json={"node_id": "node-123", "include_context": True},
        )

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert data["summary"] == "A simple test class."
        assert data["node"]["id"] == "node-123"
        assert data["node"]["type"] == "Class"
        assert data["node"]["name"] == "TestClass"

        # Verify service calls
        graph_service.find_node.assert_called_once_with("node-123")
        openai_service.generate_code_summary.assert_called_once()


def test_execute_tool_with_invalid_parameters(client):
    """Test executing a tool with invalid parameters."""
    response = client.post(
        "/v1/tools/searchGraph", json={"query": ""}  # Empty query is invalid
    )

    # Verify error response
    assert response.status_code == 400
    # Test accepts both error formats
    error_json = response.json()
    if "error" in error_json:
        assert "Search query cannot be empty" in error_json["error"]["message"]
    else:
        assert "Search query cannot be empty" in error_json["detail"]


def test_execute_nonexistent_tool(client):
    """Test executing a non-existent tool."""
    response = client.post("/v1/tools/nonexistentTool", json={})

    # Verify error response
    assert response.status_code == 404
    # Test accepts both error formats
    error_json = response.json()
    if "error" in error_json:
        assert "Tool not found" in error_json["error"]["message"]
    else:
        assert "Tool not found" in error_json["detail"]
