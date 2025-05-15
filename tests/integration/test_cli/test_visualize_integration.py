"""Integration tests for CLI visualization commands."""

import os
import tempfile
from glob import glob
from typing import Dict, Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from codestory.cli.main import app


# These tests now use auto-starting mechanism
class TestVisualizeCommands:
    """Integration tests for visualization-related CLI commands."""
    
    def test_visualize_help(self, cli_runner: CliRunner) -> None:
        """Test 'visualize --help' command."""
        # Run CLI with visualize --help
        result = cli_runner.invoke(app, ["visualize", "--help"])
        
        # Check result
        assert result.exit_code == 0
        assert "visualize" in result.output.lower()
        assert "generate" in result.output.lower()
        assert "list" in result.output.lower()
        assert "open" in result.output.lower()
    
    def test_visualize_generate(self, cli_runner: CliRunner) -> None:
        """Test 'visualize generate' command."""
        # Run visualize with service auto-start disabled to test auto-starting
        with patch("subprocess.Popen") as mock_popen:
            # This will simulate service auto-start but not actually start it
            result = cli_runner.invoke(
                app, 
                ["visualize", "generate", "--no-browser", "--type", "force", "--theme", "dark"]
            )
            
            # Check result - service should try to auto-start
            assert result.exit_code == 0
            assert "Starting service automatically" in result.output
            assert mock_popen.called
    
    def test_visualize_list(self, cli_runner: CliRunner) -> None:
        """Test 'visualize list' command."""
        # Create test files in temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            orig_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Create a test visualization file
                with open("codestory-graph-test.html", "w") as f:
                    f.write("<html><body>Test visualization</body></html>")
                
                # Run CLI with visualize list
                result = cli_runner.invoke(app, ["visualize", "list"])
                
                # Check result
                assert result.exit_code == 0
                
                if "No visualizations found" not in result.output:
                    assert "codestory-graph" in result.output
            
            finally:
                os.chdir(orig_dir)
    
    def test_visualize_help_command(self, cli_runner: CliRunner) -> None:
        """Test 'visualize help' command."""
        # Run CLI with visualize help
        result = cli_runner.invoke(app, ["visualize", "help"])
        
        # Check result
        assert result.exit_code == 0
        assert "Code Story Graph Visualization" in result.output
        assert "Visualization Types" in result.output