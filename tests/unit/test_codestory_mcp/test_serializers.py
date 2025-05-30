from typing import Any
'Unit tests for the MCP Adapter serializers.'
from unittest import mock
import pytest
from codestory_mcp.utils.serializers import NodeSerializer, RelationshipSerializer

class TestNodeSerializer:
    """Tests for the NodeSerializer class."""

    @pytest.fixture
    def mock_node(self):
        """Create a mock Neo4j node."""
        node = mock.Mock()
        node.id = 'node-123'
        node.labels = ['Class']
        node.properties = {'name': 'TestClass', 'path': '/path/to/test_class.py', 'content': 'class TestClass:\n    pass', 'created_at': '2023-01-01', 'lines': 10}

        def getitem(key: Any) -> None:
            if isinstance(key, int):
                raise IndexError(key)
            if key in node.properties:
                return node.properties[key]
            raise KeyError(key)

        def contains(key: Any):
            return key in node.properties
        node.__getitem__ = mock.Mock(side_effect=getitem)
        node.__contains__ = mock.Mock(side_effect=contains)
        node.get = mock.Mock(side_effect=lambda k, d=None: node.properties.get(k, d))
        node.items = mock.Mock(return_value=node.properties.items())
        return node

    def test_to_dict_basic(self, mock_node: Any) -> None:
        """Test basic node serialization."""
        result = NodeSerializer.to_dict(mock_node)
        assert result['id'] == 'node-123'
        assert result['type'] == 'Class'
        assert result['name'] == 'TestClass'
        assert result['path'] == '/path/to/test_class.py'
        assert result['content'] == 'class TestClass:\n    pass'
        assert 'properties' in result
        assert result['properties']['created_at'] == '2023-01-01'
        assert result['properties']['lines'] == 10

    def test_to_dict_with_score(self, mock_node: Any) -> None:
        """Test node serialization with score."""
        result = NodeSerializer.to_dict(mock_node, score=0.95)
        assert result['score'] == 0.95

    def test_to_dict_with_include_properties(self, mock_node: Any) -> None:
        """Test node serialization with included properties."""
        result = NodeSerializer.to_dict(mock_node, include_properties=['created_at'])
        assert 'properties' in result
        assert 'created_at' in result['properties']
        assert 'lines' not in result['properties']

    def test_to_dict_with_exclude_properties(self, mock_node: Any) -> None:
        """Test node serialization with excluded properties."""
        result = NodeSerializer.to_dict(mock_node, exclude_properties=['content', 'lines'])
        assert 'content' not in result
        assert 'properties' in result
        assert 'created_at' in result['properties']
        assert 'lines' not in result['properties']

    def test_to_mcp_result_with_nodes(self, mock_node: Any) -> None:
        """Test MCP result serialization with nodes."""
        mock_node2 = mock.Mock()
        mock_node2.id = 'node-456'
        mock_node2.labels = ['Function']
        mock_node2.properties = {'name': 'test_function'}

        def getitem(key: Any) -> None:
            if isinstance(key, int):
                raise IndexError(key)
            if key in mock_node2.properties:
                return mock_node2.properties[key]
            raise KeyError(key)

        def contains(key: Any):
            return key in mock_node2.properties
        mock_node2.__getitem__ = mock.Mock(side_effect=getitem)
        mock_node2.__contains__ = mock.Mock(side_effect=contains)
        mock_node2.get = mock.Mock(side_effect=lambda k, d=None: mock_node2.properties.get(k, d))
        mock_node2.items = mock.Mock(return_value=mock_node2.properties.items())
        result = NodeSerializer.to_mcp_result([mock_node, mock_node2])
        assert 'matches' in result
        assert len(result['matches']) == 2
        assert result['matches'][0]['id'] == 'node-123'
        assert result['matches'][1]['id'] == 'node-456'

    def test_to_mcp_result_with_scored_nodes(self, mock_node: Any) -> None:
        """Test MCP result serialization with nodes and scores."""
        mock_node2 = mock.Mock()
        mock_node2.id = 'node-456'
        mock_node2.labels = ['Function']
        mock_node2.properties = {'name': 'test_function'}

        def getitem(key: Any) -> None:
            if isinstance(key, int):
                raise IndexError(key)
            if key in mock_node2.properties:
                return mock_node2.properties[key]
            raise KeyError(key)

        def contains(key: Any):
            return key in mock_node2.properties
        mock_node2.__getitem__ = mock.Mock(side_effect=getitem)
        mock_node2.__contains__ = mock.Mock(side_effect=contains)
        mock_node2.get = mock.Mock(side_effect=lambda k, d=None: mock_node2.properties.get(k, d))
        mock_node2.items = mock.Mock(return_value=mock_node2.properties.items())
        result = NodeSerializer.to_mcp_result([(mock_node, 0.95), (mock_node2, 0.85)])
        assert 'matches' in result
        assert len(result['matches']) == 2
        assert result['matches'][0]['id'] == 'node-123'
        assert result['matches'][0]['score'] == 0.95
        assert result['matches'][1]['id'] == 'node-456'
        assert result['matches'][1]['score'] == 0.85

class TestRelationshipSerializer:
    """Tests for the RelationshipSerializer class."""

    @pytest.fixture
    def mock_node(self):
        """Create a mock Neo4j node."""
        node = mock.Mock()
        node.id = 'node-123'
        node.labels = ['Class']
        node.properties = {'name': 'TestClass', 'path': '/path/to/test_class.py', 'content': 'class TestClass:\n    pass'}

        def getitem(key: Any) -> None:
            if isinstance(key, int):
                raise IndexError(key)
            if key in node.properties:
                return node.properties[key]
            raise KeyError(key)

        def contains(key: Any):
            return key in node.properties
        node.__getitem__ = mock.Mock(side_effect=getitem)
        node.__contains__ = mock.Mock(side_effect=contains)
        node.get = mock.Mock(side_effect=lambda k, d=None: node.properties.get(k, d))
        node.items = mock.Mock(return_value=node.properties.items())
        return node

    @pytest.fixture
    def mock_relationship(self):
        """Create a mock Neo4j relationship."""
        rel = mock.Mock()
        rel.id = 'rel-123'
        rel.type = 'CALLS'
        start_node = mock.Mock()
        start_node.id = 'node-123'
        end_node = mock.Mock()
        end_node.id = 'node-456'
        rel.start_node = start_node
        rel.end_node = end_node
        rel.properties = {'count': 5, 'created_at': '2023-01-01'}

        def getitem(key: Any) -> None:
            if isinstance(key, int):
                raise IndexError(key)
            if key in rel.properties:
                return rel.properties[key]
            raise KeyError(key)

        def contains(key: Any):
            return key in rel.properties
        rel.__getitem__ = mock.Mock(side_effect=getitem)
        rel.__contains__ = mock.Mock(side_effect=contains)
        rel.get = mock.Mock(side_effect=lambda k, d=None: rel.properties.get(k, d))
        rel.items = mock.Mock(return_value=rel.properties.items())
        return rel

    def test_to_dict_basic(self, mock_relationship: Any) -> None:
        """Test basic relationship serialization."""
        result = RelationshipSerializer.to_dict(mock_relationship)
        assert result['id'] == 'rel-123'
        assert result['type'] == 'CALLS'
        assert result['start_node_id'] == 'node-123'
        assert result['end_node_id'] == 'node-456'
        assert 'properties' in result
        assert result['properties']['count'] == 5
        assert result['properties']['created_at'] == '2023-01-01'

    def test_to_dict_with_include_properties(self, mock_relationship: Any) -> None:
        """Test relationship serialization with included properties."""
        result = RelationshipSerializer.to_dict(mock_relationship, include_properties=['count'])
        assert 'properties' in result
        assert 'count' in result['properties']
        assert 'created_at' not in result['properties']

    def test_to_dict_with_exclude_properties(self, mock_relationship: Any) -> None:
        """Test relationship serialization with excluded properties."""
        result = RelationshipSerializer.to_dict(mock_relationship, exclude_properties=['count'])
        assert 'properties' in result
        assert 'count' not in result['properties']
        assert 'created_at' in result['properties']

    @pytest.fixture
    def mock_node2(self):
        """Create another mock Neo4j node."""
        node = mock.Mock()
        node.id = 'node-456'
        node.labels = ['Function']
        node.properties = {'name': 'test_function'}

        def getitem(key: Any) -> None:
            if isinstance(key, int):
                raise IndexError(key)
            if key in node.properties:
                return node.properties[key]
            raise KeyError(key)

        def contains(key: Any):
            return key in node.properties
        node.__getitem__ = mock.Mock(side_effect=getitem)
        node.__contains__ = mock.Mock(side_effect=contains)
        node.get = mock.Mock(side_effect=lambda k, d=None: node.properties.get(k, d))
        node.items = mock.Mock(return_value=node.properties.items())
        return node

    @pytest.fixture
    def mock_path(self, mock_node: Any, mock_relationship: Any, mock_node2: Any):
        """Create a mock path of nodes and relationships."""
        return [[mock_node, mock_relationship, mock_node2]]

    def test_to_mcp_path_result(self, mock_path: Any) -> None:
        """Test MCP path result serialization."""
        result = RelationshipSerializer.to_mcp_path_result(mock_path)
        assert 'paths' in result
        assert len(result['paths']) == 1
        path = result['paths'][0]
        assert 'elements' in path
        assert len(path['elements']) == 3
        assert path['elements'][0]['element_type'] == 'node'
        assert path['elements'][0]['id'] == 'node-123'
        assert path['elements'][0]['type'] == 'Class'
        assert path['elements'][1]['element_type'] == 'relationship'
        assert path['elements'][1]['id'] == 'rel-123'
        assert path['elements'][1]['type'] == 'CALLS'
        assert path['elements'][2]['element_type'] == 'node'
        assert path['elements'][2]['id'] == 'node-456'
        assert path['elements'][2]['type'] == 'Function'