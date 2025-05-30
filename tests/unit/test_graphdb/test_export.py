from typing import Any
'Unit tests for graph database export functionality.'
import csv
import json
import os
import tempfile
from unittest.mock import MagicMock
import pytest
from codestory.graphdb.exceptions import ExportError
from codestory.graphdb.export import export_cypher_script, export_graph_data, export_to_csv, export_to_json
from codestory.graphdb.neo4j_connector import Neo4jConnector

@pytest.fixture
def mock_connector() -> Any:
    """Create a mock Neo4jConnector."""
    connector = MagicMock(spec=Neo4jConnector)
    connector.execute_query.return_value = [{'id': 1, 'name': 'Node1', 'type': 'File'}, {'id': 2, 'name': 'Node2', 'type': 'Class'}]
    return connector

def test_export_to_json(mock_connector: Any) -> None:
    """Test exporting data to JSON."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, 'test_export.json')
        result_path = export_to_json(connector=mock_connector, output_path=output_path, query='MATCH (n) RETURN n', params={'key': 'value'}, pretty=True)
        mock_connector.execute_query.assert_called_once_with('MATCH (n) RETURN n', {'key': 'value'})
        assert os.path.exists(output_path)
        assert result_path == output_path
        with open(output_path) as f:
            data = json.load(f)
            assert len(data) == 2
            assert data[0]['id'] == 1
            assert data[0]['name'] == 'Node1'
            assert data[1]['id'] == 2
            assert data[1]['name'] == 'Node2'

def test_export_to_csv(mock_connector: Any) -> None:
    """Test exporting data to CSV."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, 'test_export.csv')
        result_path = export_to_csv(connector=mock_connector, output_path=output_path, query='MATCH (n) RETURN n', params={'key': 'value'}, delimiter=',', include_headers=True)
        mock_connector.execute_query.assert_called_once_with('MATCH (n) RETURN n', {'key': 'value'})
        assert os.path.exists(output_path)
        assert result_path == output_path
        with open(output_path, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]['id'] == '1'
            assert rows[0]['name'] == 'Node1'
            assert rows[1]['id'] == '2'
            assert rows[1]['name'] == 'Node2'

def test_export_to_csv_no_headers(mock_connector: Any) -> None:
    """Test exporting data to CSV without headers."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, 'test_export_no_headers.csv')
        export_to_csv(connector=mock_connector, output_path=output_path, query='MATCH (n) RETURN n', include_headers=False)
        with open(output_path, newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0][0] == '1'
            assert rows[0][1] == 'Node1'

def test_export_to_json_error(mock_connector: Any) -> None:
    """Test error handling in JSON export."""
    mock_connector.execute_query.side_effect = Exception('Query failed')
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, 'error_export.json')
        with pytest.raises(ExportError):
            export_to_json(connector=mock_connector, output_path=output_path, query='MATCH (n) RETURN n')
        assert not os.path.exists(output_path)

def test_export_graph_data(mock_connector: Any) -> None:
    """Test exporting complete graph data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        _ = [('MATCH (n) RETURN n', None), ('MATCH ()-[r]->() RETURN r', None)]

        def mock_execute(*args, **kwargs):
            query = args[0] if args else kwargs.get('query', '')
            if 'MATCH (n)' in query:
                return [{'n': {'id': 1, 'name': 'Test'}}]
            elif 'MATCH ()-[r]' in query:
                return [{'r': {'type': 'RELATES_TO', 'since': 2022}}]
            return []
        mock_connector.execute_query.side_effect = mock_execute
        result = export_graph_data(connector=mock_connector, output_dir=temp_dir, file_format='json')
        assert 'nodes' in result
        assert 'relationships' in result
        assert os.path.exists(result['nodes'])
        assert os.path.exists(result['relationships'])
        with open(result['nodes']) as f:
            nodes_data = json.load(f)
            assert len(nodes_data) == 1
            assert nodes_data[0]['n']['id'] == 1
        with open(result['relationships']) as f:
            rels_data = json.load(f)
            assert len(rels_data) == 1
            assert rels_data[0]['r']['type'] == 'RELATES_TO'

def test_export_cypher_script(mock_connector: Any) -> None:
    """Test exporting database as a Cypher script."""
    nodes_data = [{'n': {'labels': ['File'], 'properties': {'path': '/test/file.py', 'name': 'file.py'}}}]
    relationships_data = [{'r': {'type': 'CONTAINS', 'properties': {}}, 'source': {'labels': ['Directory'], 'properties': {'path': '/test', 'name': 'test'}}, 'target': {'labels': ['File'], 'properties': {'path': '/test/file.py', 'name': 'file.py'}}}]

    def mock_execute(query: Any, *args, **kwargs):
        if 'MATCH (n)' in query:
            return nodes_data
        elif 'MATCH ()-[r]' in query:
            return relationships_data
        return []
    mock_connector.execute_query.side_effect = mock_execute
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, 'export.cypher')
        result_path = export_cypher_script(connector=mock_connector, output_path=output_path)
        assert os.path.exists(output_path)
        assert result_path == output_path
        with open(output_path) as f:
            content = f.read()
            assert '// Neo4j database export' in content
            assert 'MATCH (n) DETACH DELETE n;' in content
            assert 'CREATE (:File' in content
            assert '{"path": "/test/file.py", "name": "file.py"}' in content
            assert 'CREATE (a)-[:CONTAINS {}]->(b);' in content