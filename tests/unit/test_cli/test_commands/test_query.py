from typing import Any
'Unit tests for the query CLI commands.'
import json
import os
import tempfile
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from codestory.cli.main import app

class TestQueryCommands:
    """Tests for the query CLI commands."""

    def test_query_help(self: Any, cli_runner: CliRunner) -> None:
        """Test 'query --help' command."""
        result = cli_runner.invoke(app, ['query', '--help'])
        assert result.exit_code == 0
        assert 'query' in result.output.lower()
        assert 'run' in result.output.lower()
        assert 'explore' in result.output.lower()
        assert 'export' in result.output.lower()

    def test_query_run_cypher(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query run' command with Cypher query."""
        mock_result = {'records': [{'count': 42}]}
        mock_service_client.execute_query.return_value = mock_result
        with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
            result = cli_runner.invoke(app, ['query', 'run', 'MATCH (n) RETURN count(n) as count'])
            assert result.exit_code == 0
            assert 'Query Results' in result.output
            assert 'count' in result.output
            assert '42' in result.output
            mock_service_client.execute_query.assert_called_once_with('MATCH (n) RETURN count(n) as count', {})

    def test_query_run_mcp(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query run' command with MCP tool call."""
        mock_result = {'results': {'name': 'test', 'path': '/path/to/test', 'type': 'class'}}
        mock_service_client.execute_query.return_value = mock_result
        with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
            result = cli_runner.invoke(app, ['query', 'run', "searchGraph('test')"])
            assert result.exit_code == 0
            assert 'Result' in result.output
            assert 'test' in result.output
            assert '/path/to/test' in result.output
            mock_service_client.execute_query.assert_called_once_with("searchGraph('test')", {})

    def test_query_run_with_parameters(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query run' command with parameters."""
        mock_result = {'records': [{'name': 'test_node'}]}
        mock_service_client.execute_query.return_value = mock_result
        with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
            result = cli_runner.invoke(app, ['query', 'run', 'MATCH (n) WHERE n.name = $name RETURN n.name', '--param', 'name=test_node'])
            assert result.exit_code == 0
            assert 'Query Results' in result.output
            assert 'test_node' in result.output
            mock_service_client.execute_query.assert_called_once()
            call_args = mock_service_client.execute_query.call_args
            assert call_args[0][0] == 'MATCH (n) WHERE n.name = $name RETURN n.name'
            assert call_args[0][1] == {'name': 'test_node'}

    def test_query_run_with_formats(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query run' command with different output formats."""
        mock_result = {'records': [{'name': 'test_node', 'type': 'class', 'path': '/path/to/test'}]}
        mock_service_client.execute_query.return_value = mock_result
        formats = ['table', 'json', 'csv', 'tree']
        for fmt in formats:
            mock_service_client.execute_query.reset_mock()
            with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
                result = cli_runner.invoke(app, ['query', 'run', 'MATCH (n) RETURN n.name, n.type, n.path', '--format', fmt])
                assert result.exit_code == 0
                assert 'test_node' in result.output
                assert '/path/to/test' in result.output
                mock_service_client.execute_query.assert_called_once()

    def test_query_run_with_limit(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query run' command with result limit."""
        mock_result = {'records': [{'id': 1, 'name': 'node1'}, {'id': 2, 'name': 'node2'}, {'id': 3, 'name': 'node3'}, {'id': 4, 'name': 'node4'}, {'id': 5, 'name': 'node5'}]}
        mock_service_client.execute_query.return_value = mock_result
        with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
            result = cli_runner.invoke(app, ['query', 'run', 'MATCH (n) RETURN n.id, n.name', '--limit', '3'])
            assert result.exit_code == 0
            assert '5 record(s)' in result.output
            assert '3 of 5 record(s) shown' in result.output
            call_args = mock_service_client.execute_query.call_args
            assert 'LIMIT 3' in call_args[0][0]

    def test_query_export(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query export' command."""
        mock_result = {'records': [{'name': 'test_node', 'type': 'class'}]}
        mock_service_client.execute_query.return_value = mock_result
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            try:
                temp_file.close()
                with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
                    result = cli_runner.invoke(app, ['query', 'export', 'MATCH (n) RETURN n.name, n.type', temp_file.name])
                    assert result.exit_code == 0
                    assert 'exported' in result.output.lower()
                    mock_service_client.execute_query.assert_called_once()
                    with open(temp_file.name) as f:
                        content = json.load(f)
                        assert 'records' in content
                        assert content['records'][0]['name'] == 'test_node'
            finally:
                os.unlink(temp_file.name)

    def test_query_export_csv(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query export' command with CSV format."""
        mock_result = {'records': [{'name': 'test_node', 'type': 'class'}, {'name': 'another_node', 'type': 'function'}]}
        mock_service_client.execute_query.return_value = mock_result
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            try:
                temp_file.close()
                with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
                    result = cli_runner.invoke(app, ['query', 'export', 'MATCH (n) RETURN n.name, n.type', temp_file.name, '--format', 'csv'])
                    assert result.exit_code == 0
                    assert 'exported' in result.output.lower()
                    mock_service_client.execute_query.assert_called_once()
                    with open(temp_file.name) as f:
                        content = f.read()
                        assert 'name,type' in content
                        assert 'test_node,class' in content.replace(' ', '')
                        assert 'another_node,function' in content.replace(' ', '')
            finally:
                os.unlink(temp_file.name)

    def test_query_explore(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query explore' command."""
        node_counts = {'records': [{'type': ['Class'], 'count': 10}, {'type': ['Function'], 'count': 20}, {'type': ['Module'], 'count': 5}]}
        class_nodes = {'records': [{'n': {'name': 'TestClass', 'path': '/path/to/class'}}]}
        function_nodes = {'records': [{'n': {'name': 'testFunction', 'path': '/path/to/function'}}]}
        module_nodes = {'records': [{'n': {'name': 'test_module', 'path': '/path/to/module'}}]}
        rel_types = {'records': [{'type': 'IMPORTS', 'count': 15}, {'type': 'DEFINES', 'count': 25}]}

        def mock_execute_query(query, params: Any=None):
            if 'labels(n) as type' in query:
                return node_counts
            elif 'MATCH (n:Class)' in query:
                return class_nodes
            elif 'MATCH (n:Function)' in query:
                return function_nodes
            elif 'MATCH (n:Module)' in query:
                return module_nodes
            elif 'MATCH ()-[r]->()' in query:
                return rel_types
            return {'records': []}
        mock_service_client.execute_query.side_effect = mock_execute_query
        with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
            result = cli_runner.invoke(app, ['query', 'explore', '--limit', '1'])
            assert result.exit_code == 0
            assert 'Graph Explorer' in result.output
            assert 'Node Types in Graph' in result.output
            assert 'Class' in result.output
            assert 'Function' in result.output
            assert 'Module' in result.output
            assert 'Relationship Types in Graph' in result.output
            assert 'IMPORTS' in result.output
            assert 'DEFINES' in result.output
            assert 'Example queries' in result.output