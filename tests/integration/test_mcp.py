"""Integration tests for the MCP Adapter."""

import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from codestory_mcp.server import create_app


@pytest.fixture
def client():
    """Create a test client for the MCP server."""
    # Set environment variables for testing
    os.environ["AUTH_ENABLED"] = "false"
    os.environ["CODE_STORY_SERVICE_URL"] = "http://localhost:8000"
    
    # Create app with mocked adapters
    with mock.patch("codestory_mcp.adapters.graph_service.GraphServiceAdapter"), \
         mock.patch("codestory_mcp.adapters.openai_service.OpenAIServiceAdapter"):
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
    # Mock the GraphServiceAdapter search method
    with mock.patch("codestory_mcp.tools.search_graph.get_graph_service") as mock_get_service:
        service = mock.Mock()
        mock_get_service.return_value = service
        
        # Mock search results
        mock_node = mock.Mock()
        mock_node.id = "node-123"
        mock_node.labels = ["Class"]
        mock_node.properties = {
            "name": "TestClass",
            "path": "/path/to/test.py"
        }
        mock_node.get = mock.Mock(side_effect=lambda k, d=None: mock_node.properties.get(k, d))
        mock_node.items = mock.Mock(return_value=mock_node.properties.items())
        
        service.search.return_value = [(mock_node, 0.95)]
        
        # Execute tool
        response = client.post(
            "/v1/tools/searchGraph",
            json={
                "query": "test query",
                "node_types": ["Class"],
                "limit": 5
            }
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
            query="test query",
            node_types=["Class"],
            limit=5
        )


def test_execute_summarize_node_tool(client):
    """Test executing the summarizeNode tool."""
    # Mock the GraphServiceAdapter and OpenAIServiceAdapter
    with mock.patch("codestory_mcp.tools.summarize_node.get_graph_service") as mock_get_graph_service, \
         mock.patch("codestory_mcp.tools.summarize_node.get_openai_service") as mock_get_openai_service:
        graph_service = mock.Mock()
        openai_service = mock.Mock()
        mock_get_graph_service.return_value = graph_service
        mock_get_openai_service.return_value = openai_service
        
        # Mock node
        mock_node = mock.Mock()
        mock_node.id = "node-123"
        mock_node.labels = ["Class"]
        mock_node.properties = {
            "name": "TestClass",
            "path": "/path/to/test.py",
            "content": "class TestClass:\n    pass"
        }
        mock_node.get = mock.Mock(side_effect=lambda k, d=None: mock_node.properties.get(k, d))
        
        graph_service.find_node.return_value = mock_node
        
        # Mock summary
        openai_service.generate_code_summary.return_value = "A simple test class."
        
        # Execute tool
        response = client.post(
            "/v1/tools/summarizeNode",
            json={
                "node_id": "node-123",
                "include_context": True
            }
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
        "/v1/tools/searchGraph",
        json={
            "query": ""  # Empty query is invalid
        }
    )
    
    # Verify error response
    assert response.status_code == 400
    assert "error" in response.json()
    assert "Search query cannot be empty" in response.json()["error"]["message"]


def test_execute_nonexistent_tool(client):
    """Test executing a non-existent tool."""
    response = client.post(
        "/v1/tools/nonexistentTool",
        json={}
    )
    
    # Verify error response
    assert response.status_code == 404
    assert "error" in response.json()
    assert "Tool not found" in response.json()["error"]["message"]