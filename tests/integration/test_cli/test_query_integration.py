"""Integration tests for CLI query commands."""
import os
from typing import Any

import pytest
from click.testing import CliRunner

from codestory.cli.main import app


@pytest.mark.require_service
class TestQueryCommands:
    """Integration tests for query-related CLI commands."""

    def test_query_help(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'query --help' command."""
        result = cli_runner.invoke(app, ['query', '--help'])
        assert result.exit_code == 0
        assert 'query' in result.output.lower()
        assert 'run' in result.output.lower()
        assert 'explore' in result.output.lower()
        assert 'export' in result.output.lower()

    def test_query_run_cypher(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'query run' command with simple Cypher query."""
        result = cli_runner.invoke(app, ['query', 'run', 'MATCH (n) RETURN count(n) as count LIMIT 5'])
        assert result.exit_code == 0
        assert 'Query Results' in result.output
        assert 'count' in result.output

    def test_query_run_with_format(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'query run' with different output formats."""
        result = cli_runner.invoke(app, ['query', 'run', 'MATCH (n) RETURN count(n) as count LIMIT 5', '--format', 'json'])
        assert result.exit_code == 0
        assert 'records' in result.output
        assert 'count' in result.output
        result = cli_runner.invoke(app, ['query', 'run', 'MATCH (n) RETURN count(n) as count LIMIT 5', '--format', 'csv'])
        assert result.exit_code == 0
        assert 'count' in result.output

    def test_query_run_with_limit(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'query run' with result limit."""
        result = cli_runner.invoke(app, ['query', 'run', 'MATCH (n) RETURN n LIMIT 100', '--limit', '3'])
        assert result.exit_code == 0
        assert 'limit=3' in result.output.lower()

    def test_query_export(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'query export' command."""
        output_file = 'test_export.json'
        try:
            result = cli_runner.invoke(app, ['query', 'export', 'MATCH (n) RETURN count(n) as count', output_file])
            assert result.exit_code == 0
            assert 'exported' in result.output.lower()
            assert os.path.exists(output_file)
            with open(output_file) as f:
                content = f.read()
                assert 'records' in content
                assert 'count' in content
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    def test_query_explore(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'query explore' command."""
        result = cli_runner.invoke(app, ['query', 'explore', '--limit', '2'])
        assert result.exit_code == 0
        assert 'Graph Explorer' in result.output
        assert 'Node Types in Graph' in result.output or 'Relationship Types in Graph' in result.output or 'Example queries' in result.output