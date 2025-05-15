"""Unit tests for the main CLI application."""

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from codestory.cli.main import app, main, custom_error_handler
from codestory.cli.client import ServiceError


class TestCliMain:
    """Tests for the main CLI application."""
    
    def test_app_initialization(self, cli_runner: CliRunner) -> None:
        """Test CLI app initialization."""
        with patch("codestory.cli.main.get_settings") as mock_get_settings:
            # Create mock settings
            mock_settings = MagicMock()
            mock_settings.service.port = 8000
            mock_get_settings.return_value = mock_settings
            
            # Run CLI with --help flag
            result = cli_runner.invoke(app, ["--help"])
            
            # Check result
            assert result.exit_code == 0
            assert "Code Story" in result.output
            
            # Check command groups
            assert "ingest" in result.output.lower()
            assert "query" in result.output.lower()
            assert "config" in result.output.lower()
            assert "service" in result.output.lower()
            assert "ask" in result.output.lower()
            assert "ui" in result.output.lower()
            assert "visualize" in result.output.lower()
    
    def test_main_with_service_error(self) -> None:
        """Test main function with ServiceError."""
        with patch("codestory.cli.main.app") as mock_app:
            with patch("codestory.cli.main.console") as mock_console:
                # Make app raise ServiceError
                mock_app.side_effect = ServiceError("Test error")
                
                # Mock sys.exit to avoid exiting the test
                with patch("codestory.cli.main.sys.exit") as mock_exit:
                    # Run main
                    main()
                    
                    # Check error handling
                    mock_console.print.assert_called_once()
                    assert "Error" in mock_console.print.call_args[0][0]
                    mock_exit.assert_called_once_with(1)
    
    def test_main_with_generic_exception(self) -> None:
        """Test main function with generic exception."""
        with patch("codestory.cli.main.app") as mock_app:
            with patch("codestory.cli.main.console") as mock_console:
                # Make app raise Exception
                mock_app.side_effect = ValueError("Test error")
                
                # Mock sys.exit to avoid exiting the test
                with patch("codestory.cli.main.sys.exit") as mock_exit:
                    # Run main
                    main()
                    
                    # Check error handling
                    mock_console.print.assert_called_once()
                    assert "Unexpected error" in mock_console.print.call_args[0][0]
                    mock_console.print_exception.assert_called_once()
                    mock_exit.assert_called_once_with(1)
    
    def test_service_url_option(self, cli_runner: CliRunner) -> None:
        """Test --service-url option."""
        with patch("codestory.cli.main.ServiceClient") as mock_client_class:
            # Create mock client instance
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Create mock settings
            mock_settings = MagicMock()

            with patch("codestory.cli.main.get_settings", return_value=mock_settings):
                # Run CLI with a real command to ensure ServiceClient is instantiated
                result = cli_runner.invoke(
                    app,
                    ["--service-url", "http://example.com", "ingest", "jobs"]
                )

                # Check client initialization
                mock_client_class.assert_called_once()
                client_args = mock_client_class.call_args[1]
                assert client_args["base_url"] == "http://example.com"
    
    def test_api_key_option(self, cli_runner: CliRunner) -> None:
        """Test --api-key option."""
        with patch("codestory.cli.main.ServiceClient") as mock_client_class:
            # Create mock client instance
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Create mock settings
            mock_settings = MagicMock()

            with patch("codestory.cli.main.get_settings", return_value=mock_settings):
                # Run CLI with a real command to ensure ServiceClient is instantiated
                result = cli_runner.invoke(
                    app,
                    ["--api-key", "test-key", "ingest", "jobs"]
                )

                # Check client initialization
                mock_client_class.assert_called_once()
                client_args = mock_client_class.call_args[1]
                assert client_args["api_key"] == "test-key"
    
    def test_no_command_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that running the CLI without a command shows help."""
        with patch("codestory.cli.main.get_settings") as mock_get_settings:
            # Create mock settings
            mock_settings = MagicMock()
            mock_settings.service.port = 8000
            mock_get_settings.return_value = mock_settings
            
            # Run CLI without any command
            result = cli_runner.invoke(app, [])
            
            # Check that help is shown
            assert result.exit_code == 0
            assert "Code Story" in result.output
            assert "Usage:" in result.output
            assert "Commands:" in result.output
    
    def test_invalid_command_suggestion(self, cli_runner: CliRunner) -> None:
        """Test that running the CLI with an invalid command gives a suggestion."""
        with patch("codestory.cli.main.get_settings") as mock_get_settings:
            # Create mock settings
            mock_settings = MagicMock()
            mock_settings.service.port = 8000
            mock_get_settings.return_value = mock_settings
            
            # Run CLI with a command that doesn't exist but is close to "service"
            # Using the native Click CLI runner to avoid pytest's capture of stderr
            result = cli_runner.invoke(app, ["servic"])
            
            # Check that help is shown
            assert result.exit_code != 0
            assert "No such command" in result.output
            assert "Did you mean" in result.output
            assert "service" in result.output
    
    def test_custom_error_handler(self) -> None:
        """Test the custom error handler."""
        with patch("click.Context.fail") as mock_fail:
            # Create a new instance of the error handler
            with custom_error_handler():
                # Make sure the original handler is saved
                assert hasattr(custom_error_handler.__enter__(custom_error_handler()), "_original_fail")
                
                # Create a mock context
                mock_ctx = MagicMock()
                
                # Call the fail method with a test message
                click.Context.fail(mock_ctx, "Some random error")
                
                # Verify that the custom handler was called and included the help suggestion
                mock_fail.assert_called_once()
                assert "Try '--help'" in mock_fail.call_args[0][1]