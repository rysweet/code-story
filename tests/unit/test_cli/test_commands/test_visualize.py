"""Unit tests for the visualize CLI commands."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from codestory.cli.main import app


class TestVisualizeCommands:
    """Tests for the visualize CLI commands."""
    
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
    
    def test_visualize_generate(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'visualize generate' command."""
        # Configure mock client
        mock_service_client.generate_visualization.return_value = "<html><body>Test visualization</body></html>"
        
        # Create temporary directory for test output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "viz.html")
            
            # Run CLI with visualize generate - no browser
            with patch("codestory.cli.commands.visualize.webbrowser.open") as mock_open:
                with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                    result = cli_runner.invoke(
                        app,
                        ["visualize", "generate", "--output", output_path, "--no-browser"]
                    )
                    
                    # Check result
                    assert result.exit_code == 0
                    assert "Visualization generated successfully" in result.output
                    assert output_path in result.output
                    
                    # Check client calls
                    mock_service_client.generate_visualization.assert_called_once()
                    
                    # Check that browser was not opened
                    mock_open.assert_not_called()
                    
                    # Check that file was created
                    assert os.path.exists(output_path)
                    with open(output_path, "r") as f:
                        content = f.read()
                        assert "Test visualization" in content
    
    def test_visualize_generate_with_options(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'visualize generate' command with various options."""
        # Configure mock client
        mock_service_client.generate_visualization.return_value = "<html><body>Test visualization</body></html>"
        
        # Create temporary directory for test output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "viz.html")
            
            # Run CLI with visualize generate with options
            with patch("codestory.cli.commands.visualize.webbrowser.open") as mock_open:
                with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                    result = cli_runner.invoke(
                        app, 
                        [
                            "visualize", "generate", 
                            "--output", output_path, 
                            "--no-browser",
                            "--type", "hierarchy",
                            "--theme", "dark",
                            "--title", "Test Visualization"
                        ]
                    )
                    
                    # Check result
                    assert result.exit_code == 0
                    assert "Type: hierarchy" in result.output
                    assert "Theme: dark" in result.output
                    
                    # Check client calls with parameters
                    mock_service_client.generate_visualization.assert_called_once()
                    params = mock_service_client.generate_visualization.call_args[0][0]
                    assert params.get("type") == "hierarchy"
                    assert params.get("theme") == "dark"
                    assert params.get("title") == "Test Visualization"
    
    def test_visualize_list(self, cli_runner: CliRunner) -> None:
        """Test 'visualize list' command with mock files."""
        # Create temporary test files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to the temporary directory
            orig_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Create test files
                open("codestory-graph-20250101-121212.html", "w").write("test")
                open("codestory-graph-20250101-121313.html", "w").write("test")
                
                # Run command
                result = cli_runner.invoke(app, ["visualize", "list"])
                
                # Check result
                assert result.exit_code == 0
                assert "Recently generated visualizations" in result.output
                assert "codestory-graph-" in result.output
                assert "20250101-121212" in result.output
                assert "20250101-121313" in result.output
                
            finally:
                # Change back to original directory
                os.chdir(orig_dir)
    
    def test_visualize_list_empty(self, cli_runner: CliRunner) -> None:
        """Test 'visualize list' command with no files."""
        # Create temporary empty directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to the temporary directory
            orig_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Run command
                result = cli_runner.invoke(app, ["visualize", "list"])
                
                # Check result
                assert result.exit_code == 0
                assert "No visualizations found" in result.output
                
            finally:
                # Change back to original directory
                os.chdir(orig_dir)
    
    def test_visualize_open(self, cli_runner: CliRunner) -> None:
        """Test 'visualize open' command."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".html") as temp_file:
            # Write test content
            temp_file.write(b"<html><body>Test</body></html>")
            temp_file.flush()
            
            # Run CLI with visualize open
            with patch("codestory.cli.commands.visualize.webbrowser.open") as mock_open:
                result = cli_runner.invoke(app, ["visualize", "open", temp_file.name])
                
                # Check result
                assert result.exit_code == 0
                assert "Opening" in result.output
                
                # Check that browser was opened
                mock_open.assert_called_once()
                assert temp_file.name in mock_open.call_args[0][0]
    
    def test_visualize_help_command(self, cli_runner: CliRunner) -> None:
        """Test 'visualize help' command."""
        # Run CLI with visualize help
        result = cli_runner.invoke(app, ["visualize", "help"])
        
        # Check result
        assert result.exit_code == 0
        assert "Code Story Graph Visualization" in result.output
        assert "Visualization Types" in result.output
        
        
    def test_visualize_service_auto_start(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test visualize generate with service auto-start."""
        # Setup the mock client to simulate the service starting
        first_call = True
        
        def side_effect(*args, **kwargs):
            nonlocal first_call
            if first_call:
                first_call = False
                raise Exception("Service not available")
            return "<html><body>Auto-started service test visualization</body></html>"
            
        mock_service_client.generate_visualization.side_effect = side_effect
        
        # Create temporary directory for test output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "viz.html")
            
            # Mock subprocess and time to simulate starting the service
            with patch("subprocess.Popen") as mock_popen:
                with patch("time.sleep"):
                    # Setup mock process
                    mock_process = MagicMock()
                    mock_popen.return_value = mock_process
                    
                    # Mock webrowser to prevent opening
                    with patch("codestory.cli.commands.visualize.webbrowser.open"):
                        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                            result = cli_runner.invoke(
                                app,
                                ["visualize", "generate", "--output", output_path, "--no-browser"]
                            )
                            
                            # Check result - should show service was started and visualization generated
                            assert result.exit_code == 0
                            assert "Starting service automatically" in result.output
                            assert "Visualization generated successfully" in result.output
                            
                            # Service should have been started
                            mock_popen.assert_called_once()
                            mock_service_client.generate_visualization.call_count >= 2