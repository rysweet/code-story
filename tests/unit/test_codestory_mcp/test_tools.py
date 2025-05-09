"""Unit tests for the MCP Adapter tools."""

from unittest import mock

import pytest
from fastapi import HTTPException, status

from codestory_mcp.tools import get_all_tools, get_tool, register_tool
from codestory_mcp.tools.base import BaseTool, ToolError
from codestory_mcp.tools.search_graph import SearchGraphTool
from codestory_mcp.tools.summarize_node import SummarizeNodeTool
from codestory_mcp.tools.path_to import PathToTool
from codestory_mcp.tools.similar_code import SimilarCodeTool


class TestToolsRegistry:
    """Tests for the tools registry."""
    
    def test_register_tool(self):
        """Test registering a tool."""
        # Create a mock tool class
        class MockTool(BaseTool):
            name = "mockTool"
            description = "A mock tool"
            parameters = {"type": "object"}
            
            async def __call__(self, params):
                return {"result": "mock"}
        
        # Register the tool
        registered = register_tool(MockTool)
        
        # Verify registration
        assert registered is MockTool
        assert get_tool("mockTool") is MockTool
    
    def test_get_tool_not_found(self):
        """Test getting a non-existent tool."""
        with pytest.raises(KeyError):
            get_tool("nonexistentTool")
    
    def test_get_all_tools(self):
        """Test getting all tools."""
        # Create and register mock tools
        class MockTool1(BaseTool):
            name = "mockTool1"
            description = "Mock tool 1"
            parameters = {"type": "object"}
            
            async def __call__(self, params):
                return {"result": "mock1"}
        
        class MockTool2(BaseTool):
            name = "mockTool2"
            description = "Mock tool 2"
            parameters = {"type": "object"}
            
            async def __call__(self, params):
                return {"result": "mock2"}
        
        # Register tools
        register_tool(MockTool1)
        register_tool(MockTool2)
        
        # Get all tools
        tools = get_all_tools()
        
        # Verify tools
        assert MockTool1 in tools
        assert MockTool2 in tools


class TestSearchGraphTool:
    """Tests for the SearchGraphTool."""
    
    @pytest.fixture
    def graph_service(self):
        """Create a mock graph service."""
        with mock.patch("codestory_mcp.tools.search_graph.get_graph_service") as mock_get_service:
            service = mock.Mock()
            mock_get_service.return_value = service
            yield service
    
    @pytest.fixture
    def metrics(self):
        """Create a mock metrics object."""
        with mock.patch("codestory_mcp.tools.search_graph.get_metrics") as mock_get_metrics:
            metrics = mock.Mock()
            mock_get_metrics.return_value = metrics
            yield metrics
    
    @pytest.fixture
    def tool(self, graph_service, metrics):
        """Create a SearchGraphTool instance."""
        return SearchGraphTool()
    
    def test_init(self, graph_service, metrics):
        """Test initialization."""
        tool = SearchGraphTool()
        
        assert tool.graph_service is graph_service
        assert tool.metrics is metrics
    
    @pytest.mark.asyncio
    async def test_call_with_empty_query(self, tool):
        """Test calling the tool with an empty query."""
        with pytest.raises(ToolError) as excinfo:
            await tool({"query": ""})
        
        assert "Search query cannot be empty" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_with_invalid_limit(self, tool):
        """Test calling the tool with an invalid limit."""
        with pytest.raises(ToolError) as excinfo:
            await tool({"query": "test", "limit": 0})
        
        assert "Limit must be a positive integer" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_success(self, tool, graph_service):
        """Test successful tool execution."""
        # Mock search results
        mock_node = mock.Mock()
        mock_node.id = "node-123"
        mock_node.labels = ["Class"]
        mock_node.properties = {"name": "TestClass", "path": "/path/to/test.py"}
        mock_node.get = mock.Mock(side_effect=lambda k, d=None: mock_node.properties.get(k, d))
        mock_node.items = mock.Mock(return_value=mock_node.properties.items())
        
        graph_service.search.return_value = [(mock_node, 0.95)]
        
        # Call the tool
        result = await tool({"query": "test query", "node_types": ["Class"], "limit": 5})
        
        # Verify graph service call
        graph_service.search.assert_called_once_with(
            query="test query",
            node_types=["Class"],
            limit=5
        )
        
        # Verify result
        assert "matches" in result
        assert len(result["matches"]) == 1
        assert result["matches"][0]["id"] == "node-123"
        assert result["matches"][0]["type"] == "Class"
        assert result["matches"][0]["score"] == 0.95
        assert "metadata" in result
        assert result["metadata"]["query"] == "test query"
        assert result["metadata"]["node_types"] == ["Class"]
        assert result["metadata"]["limit"] == 5
        assert result["metadata"]["result_count"] == 1
    
    @pytest.mark.asyncio
    async def test_call_with_search_error(self, tool, graph_service):
        """Test tool execution with search error."""
        # Mock search to raise error
        graph_service.search.side_effect = Exception("Search failed")
        
        # Call the tool and expect error
        with pytest.raises(ToolError) as excinfo:
            await tool({"query": "test query"})
        
        # Verify error
        assert "Search failed" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestSummarizeNodeTool:
    """Tests for the SummarizeNodeTool."""
    
    @pytest.fixture
    def graph_service(self):
        """Create a mock graph service."""
        with mock.patch("codestory_mcp.tools.summarize_node.get_graph_service") as mock_get_service:
            service = mock.Mock()
            mock_get_service.return_value = service
            yield service
    
    @pytest.fixture
    def openai_service(self):
        """Create a mock OpenAI service."""
        with mock.patch("codestory_mcp.tools.summarize_node.get_openai_service") as mock_get_service:
            service = mock.Mock()
            mock_get_service.return_value = service
            yield service
    
    @pytest.fixture
    def metrics(self):
        """Create a mock metrics object."""
        with mock.patch("codestory_mcp.tools.summarize_node.get_metrics") as mock_get_metrics:
            metrics = mock.Mock()
            mock_get_metrics.return_value = metrics
            yield metrics
    
    @pytest.fixture
    def tool(self, graph_service, openai_service, metrics):
        """Create a SummarizeNodeTool instance."""
        return SummarizeNodeTool()
    
    def test_init(self, graph_service, openai_service, metrics):
        """Test initialization."""
        tool = SummarizeNodeTool()
        
        assert tool.graph_service is graph_service
        assert tool.openai_service is openai_service
        assert tool.metrics is metrics
    
    @pytest.mark.asyncio
    async def test_call_with_empty_node_id(self, tool):
        """Test calling the tool with an empty node ID."""
        with pytest.raises(ToolError) as excinfo:
            await tool({"node_id": ""})
        
        assert "Node ID cannot be empty" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_with_node_without_content(self, tool, graph_service):
        """Test calling the tool with a node that has no content."""
        # Mock node without content
        mock_node = mock.Mock()
        mock_node.id = "node-123"
        mock_node.labels = ["Class"]
        mock_node.get = mock.Mock(return_value="")
        
        graph_service.find_node.return_value = mock_node
        
        # Call the tool and expect error
        with pytest.raises(ToolError) as excinfo:
            await tool({"node_id": "node-123"})
        
        # Verify error
        assert "Node does not contain code content" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_success(self, tool, graph_service, openai_service):
        """Test successful tool execution."""
        # Mock node
        mock_node = mock.Mock()
        mock_node.id = "node-123"
        mock_node.labels = ["Class"]
        mock_node.get = mock.Mock(side_effect=lambda k, d=None: {
            "name": "TestClass",
            "path": "/path/to/test.py",
            "content": "class TestClass:\n    pass"
        }.get(k, d))
        
        graph_service.find_node.return_value = mock_node
        
        # Mock summary generation
        openai_service.generate_code_summary.return_value = "A simple test class."
        
        # Call the tool
        result = await tool({"node_id": "node-123", "include_context": True})
        
        # Verify service calls
        graph_service.find_node.assert_called_once_with("node-123")
        openai_service.generate_code_summary.assert_called_once()
        
        # Verify result
        assert result["summary"] == "A simple test class."
        assert result["node"]["id"] == "node-123"
        assert result["node"]["type"] == "Class"
        assert result["node"]["name"] == "TestClass"
        assert result["metadata"]["node_id"] == "node-123"
        assert result["metadata"]["include_context"] is True


class TestPathToTool:
    """Tests for the PathToTool."""
    
    @pytest.fixture
    def graph_service(self):
        """Create a mock graph service."""
        with mock.patch("codestory_mcp.tools.path_to.get_graph_service") as mock_get_service:
            service = mock.Mock()
            mock_get_service.return_value = service
            yield service
    
    @pytest.fixture
    def openai_service(self):
        """Create a mock OpenAI service."""
        with mock.patch("codestory_mcp.tools.path_to.get_openai_service") as mock_get_service:
            service = mock.Mock()
            mock_get_service.return_value = service
            yield service
    
    @pytest.fixture
    def metrics(self):
        """Create a mock metrics object."""
        with mock.patch("codestory_mcp.tools.path_to.get_metrics") as mock_get_metrics:
            metrics = mock.Mock()
            mock_get_metrics.return_value = metrics
            yield metrics
    
    @pytest.fixture
    def tool(self, graph_service, openai_service, metrics):
        """Create a PathToTool instance."""
        return PathToTool()
    
    @pytest.mark.asyncio
    async def test_call_with_empty_from_id(self, tool):
        """Test calling the tool with an empty from_id."""
        with pytest.raises(ToolError) as excinfo:
            await tool({"from_id": "", "to_id": "node-456"})
        
        assert "Source node ID cannot be empty" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_with_empty_to_id(self, tool):
        """Test calling the tool with an empty to_id."""
        with pytest.raises(ToolError) as excinfo:
            await tool({"from_id": "node-123", "to_id": ""})
        
        assert "Target node ID cannot be empty" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_with_invalid_max_paths(self, tool):
        """Test calling the tool with an invalid max_paths."""
        with pytest.raises(ToolError) as excinfo:
            await tool({"from_id": "node-123", "to_id": "node-456", "max_paths": 0})
        
        assert "Maximum paths must be a positive integer" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_success(self, tool, graph_service, openai_service):
        """Test successful tool execution."""
        # Mock path finding results
        mock_node1 = mock.Mock()
        mock_node1.id = "node-123"
        mock_node1.labels = ["Class"]
        mock_node1.get = mock.Mock(
            side_effect=lambda k, d=None: {"name": "TestClass"}.get(k, d)
        )
        
        mock_rel = mock.Mock()
        mock_rel.id = "rel-123"
        mock_rel.type = "CALLS"
        mock_rel.start_node = mock_node1
        mock_rel.end_node = mock.Mock()
        mock_rel.end_node.id = "node-456"
        mock_rel.get = mock.Mock(return_value=None)
        
        mock_node2 = mock.Mock()
        mock_node2.id = "node-456"
        mock_node2.labels = ["Method"]
        mock_node2.get = mock.Mock(
            side_effect=lambda k, d=None: {"name": "testMethod"}.get(k, d)
        )
        
        graph_service.find_paths.return_value = [[mock_node1, mock_rel, mock_node2]]
        
        # Mock explanation generation
        openai_service.generate_path_explanation.return_value = "TestClass calls testMethod."
        
        # Call the tool
        result = await tool({
            "from_id": "node-123",
            "to_id": "node-456",
            "max_paths": 3,
            "include_explanation": True
        })
        
        # Verify service calls
        graph_service.find_paths.assert_called_once_with(
            from_id="node-123",
            to_id="node-456",
            max_paths=3
        )
        openai_service.generate_path_explanation.assert_called_once()
        
        # Verify result
        assert "paths" in result
        assert len(result["paths"]) == 1
        assert len(result["paths"][0]["elements"]) == 3
        assert "explanation" in result
        assert result["explanation"] == "TestClass calls testMethod."
        assert result["metadata"]["from_id"] == "node-123"
        assert result["metadata"]["to_id"] == "node-456"
        assert result["metadata"]["max_paths"] == 3
        assert result["metadata"]["path_count"] == 1


class TestSimilarCodeTool:
    """Tests for the SimilarCodeTool."""
    
    @pytest.fixture
    def openai_service(self):
        """Create a mock OpenAI service."""
        with mock.patch("codestory_mcp.tools.similar_code.get_openai_service") as mock_get_service:
            service = mock.Mock()
            mock_get_service.return_value = service
            yield service
    
    @pytest.fixture
    def metrics(self):
        """Create a mock metrics object."""
        with mock.patch("codestory_mcp.tools.similar_code.get_metrics") as mock_get_metrics:
            metrics = mock.Mock()
            mock_get_metrics.return_value = metrics
            yield metrics
    
    @pytest.fixture
    def tool(self, openai_service, metrics):
        """Create a SimilarCodeTool instance."""
        return SimilarCodeTool()
    
    @pytest.mark.asyncio
    async def test_call_with_empty_code(self, tool):
        """Test calling the tool with empty code."""
        with pytest.raises(ToolError) as excinfo:
            await tool({"code": ""})
        
        assert "Code snippet cannot be empty" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_with_invalid_limit(self, tool):
        """Test calling the tool with an invalid limit."""
        with pytest.raises(ToolError) as excinfo:
            await tool({"code": "def test(): pass", "limit": 0})
        
        assert "Limit must be a positive integer" in excinfo.value.message
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_call_success(self, tool, openai_service):
        """Test successful tool execution."""
        # Mock similar code results
        similar_code = [
            {
                "id": "node-123",
                "type": "Function",
                "name": "test1",
                "content": "def test1(): pass",
                "path": "/path/to/test1.py",
                "score": 0.95
            },
            {
                "id": "node-456",
                "type": "Function",
                "name": "test2",
                "content": "def test2(): pass",
                "path": "/path/to/test2.py",
                "score": 0.85
            }
        ]
        
        openai_service.find_similar_code.return_value = similar_code
        
        # Call the tool
        result = await tool({"code": "def test(): pass", "limit": 2})
        
        # Verify service call
        openai_service.find_similar_code.assert_called_once_with(
            code="def test(): pass",
            limit=2
        )
        
        # Verify result
        assert "matches" in result
        assert len(result["matches"]) == 2
        assert result["matches"][0]["id"] == "node-123"
        assert result["matches"][0]["score"] == 0.95
        assert result["matches"][1]["id"] == "node-456"
        assert result["matches"][1]["score"] == 0.85
        assert "metadata" in result
        assert result["metadata"]["code_length"] == 15
        assert result["metadata"]["limit"] == 2
        assert result["metadata"]["result_count"] == 2