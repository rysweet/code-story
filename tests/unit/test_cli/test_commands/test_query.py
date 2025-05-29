from typing import Any
"""Unit tests for the query CLI commands."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from codestory.cli.main import app


class TestQueryCommands:
    """Tests for the query CLI commands."""

    def test_query_help(self, cli_runner: CliRunner) -> None:
        """Test 'query --help' command."""
        # Run CLI with query --help
        result = cli_runner.invoke(app, ["query", "--help"])

        # Check result
        assert result.exit_code == 0
        assert "query" in result.output.lower()
        assert "run" in result.output.lower()
        assert "explore" in result.output.lower()
        assert "export" in result.output.lower()

    def test_query_run_cypher(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query run' command with Cypher query."""
        # Configure mock client with sample Cypher query result
        mock_result = {"records": [{"count": 42}]}
        mock_service_client.execute_query.return_value = mock_result

        # Run CLI with query run
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(app, ["query", "run", "MATCH (n) RETURN count(n) as count"])

            # Check result
            assert result.exit_code == 0
            assert "Query Results" in result.output
            assert "count" in result.output
            assert "42" in result.output

            # Check client calls
            mock_service_client.execute_query.assert_called_once_with(
                "MATCH (n) RETURN count(n) as count", {}
            )

    def test_query_run_mcp(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query run' command with MCP tool call."""
        # Configure mock client with sample MCP tool result
        mock_result = {"results": {"name": "test", "path": "/path/to/test", "type": "class"}}
        mock_service_client.execute_query.return_value = mock_result

        # Run CLI with query run
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(app, ["query", "run", "searchGraph('test')"])

            # Check result
            assert result.exit_code == 0
            assert "Result" in result.output
            assert "test" in result.output
            assert "/path/to/test" in result.output

            # Check client calls
            mock_service_client.execute_query.assert_called_once_with("searchGraph('test')", {})

    def test_query_run_with_parameters(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'query run' command with parameters."""
        # Configure mock client
        mock_result = {"records": [{"name": "test_node"}]}
        mock_service_client.execute_query.return_value = mock_result

        # Run CLI with query run and parameters
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(
                app,
                [
                    "query",
                    "run",
                    "MATCH (n) WHERE n.name = $name RETURN n.name",
                    "--param",
                    "name=test_node",
                ],
            )

            # Check result
            assert result.exit_code == 0
            assert "Query Results" in result.output
            assert "test_node" in result.output

            # Check client calls with parameters
            mock_service_client.execute_query.assert_called_once()
            call_args = mock_service_client.execute_query.call_args
            assert call_args[0][0] == "MATCH (n) WHERE n.name = $name RETURN n.name"
            assert call_args[0][1] == {"name": "test_node"}

    def test_query_run_with_formats(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'query run' command with different output formats."""
        # Configure mock client
        mock_result = {"records": [{"name": "test_node", "type": "class", "path": "/path/to/test"}]}
        mock_service_client.execute_query.return_value = mock_result

        formats = ["table", "json", "csv", "tree"]

        for fmt in formats:
            mock_service_client.execute_query.reset_mock()

            # Run CLI with query run and format
            with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                result = cli_runner.invoke(
                    app,
                    [
                        "query",
                        "run",
                        "MATCH (n) RETURN n.name, n.type, n.path",
                        "--format",
                        fmt,
                    ],
                )

                # Check result
                assert result.exit_code == 0
                assert "test_node" in result.output
                assert "/path/to/test" in result.output

                # Check client calls
                mock_service_client.execute_query.assert_called_once()

    def test_query_run_with_limit(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'query run' command with result limit."""
        # Configure mock client with multiple records
        mock_result = {
            "records": [
                {"id": 1, "name": "node1"},
                {"id": 2, "name": "node2"},
                {"id": 3, "name": "node3"},
                {"id": 4, "name": "node4"},
                {"id": 5, "name": "node5"},
            ]
        }
        mock_service_client.execute_query.return_value = mock_result

        # Run CLI with query run and limit
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(
                app, ["query", "run", "MATCH (n) RETURN n.id, n.name", "--limit", "3"]
            )

            # Check result
            assert result.exit_code == 0
            assert "5 record(s)" in result.output  # Total records
            assert "3 of 5 record(s) shown" in result.output  # Limited display

            # Check that limit is added to the query
            call_args = mock_service_client.execute_query.call_args
            assert "LIMIT 3" in call_args[0][0]

    def test_query_export(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query export' command."""
        # Configure mock client
        mock_result = {"records": [{"name": "test_node", "type": "class"}]}
        mock_service_client.execute_query.return_value = mock_result

        # Create temporary file for test output
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            try:
                # Close file to allow writing on Windows
                temp_file.close()

                # Run CLI with query export
                with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                    result = cli_runner.invoke(
                        app,
                        [
                            "query",
                            "export",
                            "MATCH (n) RETURN n.name, n.type",
                            temp_file.name,
                        ],
                    )

                    # Check result
                    assert result.exit_code == 0
                    assert "exported" in result.output.lower()

                    # Check client calls
                    mock_service_client.execute_query.assert_called_once()

                    # Check file content
                    with open(temp_file.name) as f:
                        content = json.load(f)
                        assert "records" in content
                        assert content["records"][0]["name"] == "test_node"

            finally:
                # Clean up
                os.unlink(temp_file.name)

    def test_query_export_csv(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query export' command with CSV format."""
        # Configure mock client
        mock_result = {
            "records": [
                {"name": "test_node", "type": "class"},
                {"name": "another_node", "type": "function"},
            ]
        }
        mock_service_client.execute_query.return_value = mock_result

        # Create temporary file for test output
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
            try:
                # Close file to allow writing on Windows
                temp_file.close()

                # Run CLI with query export
                with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                    result = cli_runner.invoke(
                        app,
                        [
                            "query",
                            "export",
                            "MATCH (n) RETURN n.name, n.type",
                            temp_file.name,
                            "--format",
                            "csv",
                        ],
                    )

                    # Check result
                    assert result.exit_code == 0
                    assert "exported" in result.output.lower()

                    # Check client calls
                    mock_service_client.execute_query.assert_called_once()

                    # Check file content
                    with open(temp_file.name) as f:
                        content = f.read()
                        assert "name,type" in content
                        assert "test_node,class" in content.replace(" ", "")
                        assert "another_node,function" in content.replace(" ", "")

            finally:
                # Clean up
                os.unlink(temp_file.name)

    def test_query_explore(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'query explore' command."""
        # Configure mock client for several queries

        # First query - node types and counts
        node_counts = {
            "records": [
                {"type": ["Class"], "count": 10},
                {"type": ["Function"], "count": 20},
                {"type": ["Module"], "count": 5},
            ]
        }

        # Sample nodes of each type
        class_nodes = {"records": [{"n": {"name": "TestClass", "path": "/path/to/class"}}]}

        function_nodes = {"records": [{"n": {"name": "testFunction", "path": "/path/to/function"}}]}

        module_nodes = {"records": [{"n": {"name": "test_module", "path": "/path/to/module"}}]}

        # Relationship types
        rel_types = {
            "records": [
                {"type": "IMPORTS", "count": 15},
                {"type": "DEFINES", "count": 25},
            ]
        }

        # Set up mock to return different results for different queries
        def mock_execute_query: Any(query, params: Any=None):
            if "labels(n) as type" in query:
                return node_counts
            elif "MATCH (n:Class)" in query:
                return class_nodes
            elif "MATCH (n:Function)" in query:
                return function_nodes
            elif "MATCH (n:Module)" in query:
                return module_nodes
            elif "MATCH ()-[r]->()" in query:
                return rel_types
            return {"records": []}

        mock_service_client.execute_query.side_effect = mock_execute_query

        # Run CLI with query explore
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(app, ["query", "explore", "--limit", "1"])

            # Check result
            assert result.exit_code == 0
            assert "Graph Explorer" in result.output
            assert "Node Types in Graph" in result.output
            assert "Class" in result.output
            assert "Function" in result.output
            assert "Module" in result.output
            assert "Relationship Types in Graph" in result.output
            assert "IMPORTS" in result.output
            assert "DEFINES" in result.output
            assert "Example queries" in result.output
