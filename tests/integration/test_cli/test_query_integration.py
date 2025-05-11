"""Integration tests for CLI query commands."""

from typing import Dict, Any

import pytest
from click.testing import CliRunner

from codestory.cli.main import app


class TestQueryCommands:
    """Integration tests for query-related CLI commands."""
    
    @pytest.mark.integration
    @pytest.mark.require_service
    def test_query_simple_cypher(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'query' command with a simple Cypher query."""
        # Run a simple query
        result = cli_runner.invoke(app, ["query", "MATCH (n) RETURN count(n) as count LIMIT 5"])
        
        # Check result
        assert result.exit_code == 0
        assert "Query Results" in result.output
        
        # The count should be present (even if it's 0)
        assert "count" in result.output
    
    @pytest.mark.integration
    @pytest.mark.require_service
    def test_ask_question(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'ask' command with a simple question."""
        # Ask a simple question about the codebase
        result = cli_runner.invoke(app, ["ask", "What entities are in the database?"])
        
        # Check result
        assert result.exit_code == 0
        
        # The response should be present (even if it's saying there's no data)
        assert len(result.output.strip()) > 0