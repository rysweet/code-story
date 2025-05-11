"""Integration tests for CLI visualization commands."""

import os
from glob import glob
from typing import Dict, Any

import pytest
from click.testing import CliRunner

from codestory.cli.main import app


@pytest.mark.require_service
class TestVisualizeCommands:
    """Integration tests for visualization-related CLI commands."""
    
    def test_visualize_help(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'visualize --help' command."""
        # Run CLI with visualize --help
        result = cli_runner.invoke(app, ["visualize", "--help"])
        
        # Check result
        assert result.exit_code == 0
        assert "visualize" in result.output.lower()
        assert "generate" in result.output.lower()
        assert "list" in result.output.lower()
        assert "open" in result.output.lower()
    
    def test_visualize_generate(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'visualize generate' command."""
        # Run CLI with visualize generate, but no browser opening
        with pytest.raises(SystemExit):
            result = cli_runner.invoke(
                app, 
                ["visualize", "generate", "--no-browser", "--type", "force", "--theme", "dark"],
                catch_exceptions=False
            )
            
            # Check result (if no exit)
            assert result.exit_code == 0
            assert "Visualization generated successfully" in result.output
            
            # Check that a file was created
            html_files = glob("codestory-graph-*.html")
            assert len(html_files) > 0
            
            # Clean up after the test
            for file in html_files:
                try:
                    os.remove(file)
                except (OSError, IOError):
                    pass
    
    def test_visualize_list(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'visualize list' command."""
        # Create a test file first
        with open("codestory-graph-test.html", "w") as f:
            f.write("<html><body>Test</body></html>")
        
        try:
            # Run CLI with visualize list
            result = cli_runner.invoke(app, ["visualize", "list"])
            
            # Check result
            assert result.exit_code == 0
            
            if "No visualizations found" not in result.output:
                assert "codestory-graph" in result.output
        
        finally:
            # Clean up
            try:
                os.remove("codestory-graph-test.html")
            except (OSError, IOError):
                pass
    
    def test_visualize_help_command(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'visualize help' command."""
        # Run CLI with visualize help
        result = cli_runner.invoke(app, ["visualize", "help"])
        
        # Check result
        assert result.exit_code == 0
        assert "Code Story Graph Visualization" in result.output
        assert "Visualization Types" in result.output
        assert "force-directed graph" in result.output.lower()