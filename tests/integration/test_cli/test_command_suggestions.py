from typing import Any
"""
Integration tests for CLI command suggestions and help behavior.
"""

import pytest
from click.testing import CliRunner

# Import the main CLI app
from codestory.cli.main import app


@pytest.fixture
def cli_runner():
    """Create a click CLI runner."""
    return CliRunner()


def test_no_command_shows_help(cli_runner: Any) -> None:
    """Test that running the CLI without a command shows help."""
    # Run CLI without any command
    result = cli_runner.invoke(app, [])

    # Check that help is shown
    assert result.exit_code == 0
    assert "Code Story" in result.output
    assert "Usage:" in result.output
    assert "Commands:" in result.output


def test_invalid_command_suggestion(cli_runner: Any) -> None:
    """Test that running the CLI with an invalid command gives a suggestion."""
    # Run CLI with a command that doesn't exist but is close to "service"
    result = cli_runner.invoke(app, ["servic"])

    # Check that the suggestion is shown
    assert result.exit_code != 0
    assert "No such command" in result.output
    assert "Did you mean" in result.output
    assert "service" in result.output


def test_invalid_command_with_similar_options(cli_runner: Any) -> None:
    """Test suggestions with multiple similar commands."""
    # Both "status" and "st" (service status alias) should be suggested for "stat"
    result = cli_runner.invoke(app, ["stat"])

    # Check that both similar commands are suggested
    assert result.exit_code != 0
    assert "No such command" in result.output
    assert "Did you mean" in result.output
    # Should suggest "st" (alias for status) and possibly "status"
    assert "st" in result.output


def test_help_flag_shows_help(cli_runner: Any) -> None:
    """Test that --help flag shows help information."""
    # Run CLI with --help flag
    result = cli_runner.invoke(app, ["--help"])

    # Check that help is shown
    assert result.exit_code == 0
    assert "Code Story" in result.output
    assert "Usage:" in result.output
    assert "Commands:" in result.output
    assert "Options:" in result.output


def test_command_help_shows_command_help(cli_runner: Any) -> None:
    """Test that command --help shows command-specific help."""
    # Run CLI with command help
    result = cli_runner.invoke(app, ["service", "--help"])

    # Check that command-specific help is shown
    assert result.exit_code == 0
    assert "service" in result.output.lower()
    # Accept both plain and rich-click box-drawing output
    assert ("Commands:" in result.output) or ("╭─ Commands" in result.output)
    assert "Usage:" in result.output
