"""Unit tests for the MCP Adapter service adapters."""

from unittest import mock

import httpx
import pytest
from fastapi import status

from codestory_mcp.adapters.graph_service import (
    GraphServiceAdapter, MockNode, MockRelationship, get_graph_service
)
from codestory_mcp.adapters.openai_service import OpenAIServiceAdapter, get_openai_service
from codestory_mcp.tools.base import ToolError


class TestMockNode:
    """Tests for the MockNode class."""
    
    def test_init(self):
        """Test initialization."""
        node = MockNode("node-123", ["Class"], {"name": "TestClass"})
        
        assert node.id == "node-123"
        assert node.labels == ["Class"]
        assert node.properties == {"name": "TestClass"}
    
    def test_get(self):
        """Test get method."""
        node = MockNode("node-123", ["Class"], {"name": "TestClass"})
        
        assert node.get("name") == "TestClass"
        assert node.get("nonexistent") is None
        assert node.get("nonexistent", "default") == "default"
    
    def test_items(self):
        """Test items method."""
        node = MockNode("node-123", ["Class"], {"name": "TestClass", "path": "/path"})
        
        items = node.items()
        assert len(items) == 2
        assert ("name", "TestClass") in items
        assert ("path", "/path") in items
    
    def test_getitem(self):
        """Test __getitem__ method."""
        node = MockNode("node-123", ["Class"], {"name": "TestClass"})
        
        assert node["name"] == "TestClass"
        
        with pytest.raises(KeyError):
            node["nonexistent"]


class TestMockRelationship:
    """Tests for the MockRelationship class."""
    
    def test_init(self):
        """Test initialization."""
        rel = MockRelationship(
            "rel-123", "CALLS", "node-123", "node-456", {"count": 5}
        )
        
        assert rel.id == "rel-123"
        assert rel.type == "CALLS"
        assert rel.properties == {"count": 5}
        assert rel.start_node.id == "node-123"
        assert rel.end_node.id == "node-456"
    
    def test_get(self):
        """Test get method."""
        rel = MockRelationship(
            "rel-123", "CALLS", "node-123", "node-456", {"count": 5}
        )
        
        assert rel.get("count") == 5
        assert rel.get("nonexistent") is None
        assert rel.get("nonexistent", "default") == "default"
    
    def test_items(self):
        """Test items method."""
        rel = MockRelationship(
            "rel-123", "CALLS", "node-123", "node-456", {"count": 5, "timestamp": "now"}
        )
        
        items = rel.items()
        assert len(items) == 2
        assert ("count", 5) in items
        assert ("timestamp", "now") in items
    
    def test_getitem(self):
        """Test __getitem__ method."""
        rel = MockRelationship(
            "rel-123", "CALLS", "node-123", "node-456", {"count": 5}
        )
        
        assert rel["count"] == 5
        
        with pytest.raises(KeyError):
            rel["nonexistent"]


class TestGraphServiceAdapter:
    """Tests for the GraphServiceAdapter class."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create a mock settings object."""
        with mock.patch("codestory_mcp.adapters.graph_service.get_mcp_settings") as mock_get_settings:
            settings = mock.Mock()
            settings.code_story_service_url = "http://localhost:8000"
            mock_get_settings.return_value = settings
            yield settings
    
    @pytest.fixture
    def mock_metrics(self):
        """Create a mock metrics object."""
        with mock.patch("codestory_mcp.adapters.graph_service.get_metrics") as mock_get_metrics:
            metrics = mock.Mock()
            mock_get_metrics.return_value = metrics
            yield metrics
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        with mock.patch("codestory_mcp.adapters.graph_service.httpx.AsyncClient") as mock_client_cls:
            client = mock.Mock()
            mock_client_cls.return_value = client
            yield client
    
    @pytest.fixture
    def adapter(self, mock_settings, mock_metrics, mock_client):
        """Create a GraphServiceAdapter instance."""
        return GraphServiceAdapter()
    
    def test_init(self, mock_settings, mock_metrics, mock_client):
        """Test initialization."""
        adapter = GraphServiceAdapter()
        
        assert adapter.base_url == "http://localhost:8000"
        assert adapter.metrics is mock_metrics
        assert adapter.client is mock_client
    
    def test_init_with_custom_url(self, mock_settings, mock_metrics, mock_client):
        """Test initialization with custom URL."""
        # Set a default value for code_story_service_url in settings
        mock_settings.code_story_service_url = "http://default:8000"

        adapter = GraphServiceAdapter(base_url="http://custom:8000")

        assert adapter.base_url == "http://custom:8000"
        assert adapter.metrics is mock_metrics
        assert adapter.client is mock_client
    
    @pytest.mark.asyncio
    async def test_search_success(self, adapter, mock_client):
        """Test successful search."""
        # Mock response
        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": [
                {
                    "id": "node-123",
                    "type": "Class",
                    "properties": {
                        "name": "TestClass",
                        "path": "/path/to/test.py"
                    },
                    "score": 0.95
                },
                {
                    "id": "node-456",
                    "type": "Function",
                    "properties": {
                        "name": "testFunction",
                    },
                    "score": 0.85
                }
            ]
        }
        mock_client.post.return_value = response
        
        # Execute search
        results = await adapter.search(
            query="test",
            node_types=["Class", "Function"],
            limit=10
        )
        
        # Verify request
        mock_client.post.assert_called_once_with(
            "/v1/query/search",
            json={
                "query": "test",
                "node_types": ["Class", "Function"],
                "limit": 10
            }
        )
        
        # Verify results
        assert len(results) == 2
        assert isinstance(results[0][0], MockNode)
        assert results[0][0].id == "node-123"
        assert results[0][0].labels == ["Class"]
        assert results[0][0].properties["name"] == "TestClass"
        assert results[0][1] == 0.95
        
        assert isinstance(results[1][0], MockNode)
        assert results[1][0].id == "node-456"
        assert results[1][0].labels == ["Function"]
        assert results[1][0].properties["name"] == "testFunction"
        assert results[1][1] == 0.85
    
    @pytest.mark.asyncio
    async def test_search_error(self, adapter, mock_client, mock_metrics):
        """Test search with error response."""
        # Mock error response
        response = mock.Mock()
        response.status_code = 500
        response.text = "Internal server error"
        mock_client.post.return_value = response
        
        # Execute search and expect error
        with pytest.raises(ToolError) as excinfo:
            await adapter.search(query="test")
        
        # Verify error
        assert "Search failed" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_502_BAD_GATEWAY
        
        # Verify metrics
        mock_metrics.record_service_api_call.assert_called_once()
        assert mock_metrics.record_service_api_call.call_args[0][0] == "/v1/query/search"
        assert mock_metrics.record_service_api_call.call_args[0][1] == "error"
    
    @pytest.mark.asyncio
    async def test_search_network_error(self, adapter, mock_client, mock_metrics):
        """Test search with network error."""
        # Mock network error
        mock_client.post.side_effect = httpx.RequestError("Connection error")
        
        # Execute search and expect error
        with pytest.raises(ToolError) as excinfo:
            await adapter.search(query="test")
        
        # Verify error
        assert "Search failed" in excinfo.value.message
        assert "Connection error" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_502_BAD_GATEWAY
        
        # Verify metrics
        mock_metrics.record_service_api_call.assert_called_once()
        assert mock_metrics.record_service_api_call.call_args[0][0] == "/v1/query/search"
        assert mock_metrics.record_service_api_call.call_args[0][1] == "error"
    
    @pytest.mark.asyncio
    async def test_find_node_success(self, adapter, mock_client):
        """Test successful node lookup."""
        # Mock response
        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "id": "node-123",
                "type": "Class",
                "properties": {
                    "name": "TestClass",
                    "path": "/path/to/test.py",
                    "content": "class TestClass:\n    pass"
                }
            }
        }
        mock_client.get.return_value = response
        
        # Execute find_node
        node = await adapter.find_node("node-123")
        
        # Verify request
        mock_client.get.assert_called_once_with("/v1/query/node/node-123")
        
        # Verify result
        assert isinstance(node, MockNode)
        assert node.id == "node-123"
        assert node.labels == ["Class"]
        assert node.properties["name"] == "TestClass"
        assert node.properties["path"] == "/path/to/test.py"
        assert node.properties["content"] == "class TestClass:\n    pass"
    
    @pytest.mark.asyncio
    async def test_find_node_not_found(self, adapter, mock_client, mock_metrics):
        """Test node lookup with not found error."""
        # Mock not found response
        response = mock.Mock()
        response.status_code = 404
        response.text = "Node not found"
        mock_client.get.return_value = response
        
        # Execute find_node and expect error
        with pytest.raises(ToolError) as excinfo:
            await adapter.find_node("nonexistent")
        
        # Verify error
        assert "Node not found" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND
        
        # Verify metrics
        mock_metrics.record_service_api_call.assert_called_once()
        assert mock_metrics.record_service_api_call.call_args[0][0] == "/v1/query/node/nonexistent"
        assert mock_metrics.record_service_api_call.call_args[0][1] == "error"
    
    @pytest.mark.asyncio
    async def test_find_paths_success(self, adapter, mock_client):
        """Test successful path finding."""
        # Mock response
        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": [
                {
                    "elements": [
                        {
                            "element_type": "node",
                            "id": "node-123",
                            "type": "Class",
                            "properties": {
                                "name": "TestClass"
                            }
                        },
                        {
                            "element_type": "relationship",
                            "id": "rel-123",
                            "type": "CALLS",
                            "start_node_id": "node-123",
                            "end_node_id": "node-456",
                            "properties": {}
                        },
                        {
                            "element_type": "node",
                            "id": "node-456",
                            "type": "Function",
                            "properties": {
                                "name": "testFunction"
                            }
                        }
                    ]
                }
            ]
        }
        mock_client.post.return_value = response
        
        # Execute find_paths
        paths = await adapter.find_paths(
            from_id="node-123",
            to_id="node-456",
            max_paths=3
        )
        
        # Verify request
        mock_client.post.assert_called_once_with(
            "/v1/query/paths",
            json={
                "from_id": "node-123",
                "to_id": "node-456",
                "max_paths": 3
            }
        )
        
        # Verify results
        assert len(paths) == 1
        assert len(paths[0]) == 3
        
        assert isinstance(paths[0][0], MockNode)
        assert paths[0][0].id == "node-123"
        assert paths[0][0].labels == ["Class"]
        assert paths[0][0].properties["name"] == "TestClass"
        
        assert isinstance(paths[0][1], MockRelationship)
        assert paths[0][1].id == "rel-123"
        assert paths[0][1].type == "CALLS"
        assert paths[0][1].start_node.id == "node-123"
        assert paths[0][1].end_node.id == "node-456"
        
        assert isinstance(paths[0][2], MockNode)
        assert paths[0][2].id == "node-456"
        assert paths[0][2].labels == ["Function"]
        assert paths[0][2].properties["name"] == "testFunction"
    
    def test_get_graph_service_singleton(self, mock_settings):
        """Test that get_graph_service returns a singleton."""
        service1 = get_graph_service()
        service2 = get_graph_service()
        
        assert service1 is service2


class TestOpenAIServiceAdapter:
    """Tests for the OpenAIServiceAdapter class."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAI client."""
        with mock.patch("codestory_mcp.adapters.openai_service.OpenAIClient") as mock_client_cls:
            client = mock.Mock()
            mock_client_cls.return_value = client
            yield client
    
    @pytest.fixture
    def mock_metrics(self):
        """Create a mock metrics object."""
        with mock.patch("codestory_mcp.adapters.openai_service.get_metrics") as mock_get_metrics:
            metrics = mock.Mock()
            mock_get_metrics.return_value = metrics
            yield metrics
    
    @pytest.fixture
    def adapter(self, mock_client, mock_metrics):
        """Create an OpenAIServiceAdapter instance."""
        return OpenAIServiceAdapter()
    
    def test_init(self, mock_client, mock_metrics):
        """Test initialization."""
        adapter = OpenAIServiceAdapter()
        
        assert adapter.client is mock_client
        assert adapter.metrics is mock_metrics
    
    def test_init_with_custom_client(self, mock_metrics):
        """Test initialization with custom client."""
        custom_client = mock.Mock()
        adapter = OpenAIServiceAdapter(client=custom_client)
        
        assert adapter.client is custom_client
        assert adapter.metrics is mock_metrics
    
    @pytest.mark.asyncio
    async def test_generate_code_summary_success(self, adapter, mock_client, mock_metrics):
        """Test successful code summary generation."""
        # Mock response
        response = mock.Mock()
        response.choices = [mock.Mock()]
        response.choices[0].message.content = "A simple test class."
        mock_client.create_chat_completion.return_value = response
        
        # Execute summary generation
        summary = await adapter.generate_code_summary(
            code="class TestClass:\n    pass",
            context="Test context",
            max_tokens=500
        )
        
        # Verify client call
        mock_client.create_chat_completion.assert_called_once()
        
        # Verify request
        request = mock_client.create_chat_completion.call_args[0][0]
        assert len(request.messages) == 3
        assert request.messages[0].role == "system"
        assert request.messages[1].role == "user"
        assert "Test context" in request.messages[1].content
        assert request.messages[2].role == "user"
        assert "class TestClass" in request.messages[2].content
        assert request.max_tokens == 500
        assert request.temperature == 0.3
        assert request.model == "gpt-4-turbo"
        
        # Verify result
        assert summary == "A simple test class."
        
        # Verify metrics
        mock_metrics.record_service_api_call.assert_called_once()
        assert mock_metrics.record_service_api_call.call_args[0][0] == "openai_summary"
        assert mock_metrics.record_service_api_call.call_args[0][1] == "success"
    
    @pytest.mark.asyncio
    async def test_generate_code_summary_error(self, adapter, mock_client, mock_metrics):
        """Test code summary generation with error."""
        # Mock error
        mock_client.create_chat_completion.side_effect = Exception("API error")
        
        # Execute summary generation and expect error
        with pytest.raises(ToolError) as excinfo:
            await adapter.generate_code_summary(code="class TestClass:\n    pass")
        
        # Verify error
        assert "Code summarization failed" in excinfo.value.message
        assert "API error" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_502_BAD_GATEWAY
        
        # Verify metrics
        mock_metrics.record_service_api_call.assert_called_once()
        assert mock_metrics.record_service_api_call.call_args[0][0] == "openai_summary"
        assert mock_metrics.record_service_api_call.call_args[0][1] == "error"
    
    @pytest.mark.asyncio
    async def test_generate_path_explanation_success(self, adapter, mock_client, mock_metrics):
        """Test successful path explanation generation."""
        # Mock response
        response = mock.Mock()
        response.choices = [mock.Mock()]
        response.choices[0].message.content = "Class TestClass calls method testMethod."
        mock_client.create_chat_completion.return_value = response
        
        # Execute path explanation generation
        path_elements = [
            {
                "element_type": "node",
                "id": "node-123",
                "type": "Class",
                "name": "TestClass",
                "content": "class TestClass:\n    pass"
            },
            {
                "element_type": "relationship",
                "id": "rel-123",
                "type": "CALLS"
            },
            {
                "element_type": "node",
                "id": "node-456",
                "type": "Method",
                "name": "testMethod",
                "content": "def testMethod():\n    pass"
            }
        ]
        
        explanation = await adapter.generate_path_explanation(
            path_elements=path_elements,
            max_tokens=300
        )
        
        # Verify client call
        mock_client.create_chat_completion.assert_called_once()
        
        # Verify request
        request = mock_client.create_chat_completion.call_args[0][0]
        assert len(request.messages) == 2
        assert request.messages[0].role == "system"
        assert request.messages[1].role == "user"
        assert "TestClass" in request.messages[1].content
        assert "CALLS" in request.messages[1].content
        assert "testMethod" in request.messages[1].content
        assert request.max_tokens == 300
        assert request.temperature == 0.3
        assert request.model == "gpt-4-turbo"
        
        # Verify result
        assert explanation == "Class TestClass calls method testMethod."
        
        # Verify metrics
        mock_metrics.record_service_api_call.assert_called_once()
        assert mock_metrics.record_service_api_call.call_args[0][0] == "openai_path_explanation"
        assert mock_metrics.record_service_api_call.call_args[0][1] == "success"
    
    @pytest.mark.asyncio
    async def test_find_similar_code_success(self, adapter, mock_client, mock_metrics):
        """Test successful similar code search."""
        # Mock embedding creation
        mock_client.create_embedding.return_value = [0.1, 0.2, 0.3]
        
        # Execute similar code search
        results = await adapter.find_similar_code(
            code="def test(): pass",
            limit=5
        )
        
        # Verify client call
        mock_client.create_embedding.assert_called_once_with("def test(): pass")
        
        # Verify results (placeholder implementation)
        assert len(results) == 5
        assert results[0]["type"] == "Function"
        assert "similarFunction0" in results[0]["name"]
        assert results[0]["score"] == 1.0
        
        # Verify metrics
        assert mock_metrics.record_service_api_call.call_count == 2
        assert mock_metrics.record_service_api_call.call_args_list[0][0][0] == "openai_embedding"
        assert mock_metrics.record_service_api_call.call_args_list[1][0][0] == "similar_code"
        assert mock_metrics.record_graph_operation.called
    
    def test_get_openai_service_singleton(self):
        """Test that get_openai_service returns a singleton."""
        service1 = get_openai_service()
        service2 = get_openai_service()
        
        assert service1 is service2