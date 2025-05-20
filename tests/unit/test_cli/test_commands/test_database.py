"""Unit tests for the database CLI commands."""

import pytest
from unittest.mock import MagicMock
from click.testing import CliRunner

from codestory.cli.commands.database import database, clear_database
from codestory.cli.client import ServiceError


@pytest.fixture
def mock_client():
    """Mock service client."""
    client = MagicMock()
    client.clear_database.return_value = {
        "status": "success",
        "message": "Database successfully cleared",
        "timestamp": "2023-05-01T12:34:56Z"
    }
    return client


@pytest.fixture
def mock_console():
    """Mock console."""
    return MagicMock()


@pytest.fixture
def cli_context(mock_client, mock_console):
    """Click context with client and console."""
    ctx = MagicMock()
    ctx.obj = {
        "client": mock_client,
        "console": mock_console
    }
    return ctx


def test_database_group():
    """Test the database command group."""
    runner = CliRunner()
    result = runner.invoke(database, ["--help"])
    assert result.exit_code == 0
    assert "Manage the graph database" in result.output


def test_clear_database_with_force(cli_context, mock_client, mock_console):
    """Test clearing the database with force option."""
    runner = CliRunner()
    result = runner.invoke(clear_database, ["--force"], obj=cli_context.obj)
    
    assert result.exit_code == 0
    mock_client.clear_database.assert_called_once_with(confirm=True)
    assert mock_console.print.call_count >= 2  # Opening message + result


def test_clear_database_error(cli_context, mock_client, mock_console):
    """Test handling errors when clearing the database."""
    # Set up the error
    mock_client.clear_database.side_effect = ServiceError("Failed to clear database")
    
    runner = CliRunner()
    result = runner.invoke(clear_database, ["--force"], obj=cli_context.obj)
    
    assert result.exit_code == 0  # Command completes but shows error
    mock_client.clear_database.assert_called_once_with(confirm=True)
    # Check that error was printed
    error_calls = [call for call in mock_console.print.call_args_list if "Error" in str(call)]
    assert len(error_calls) > 0