from typing import Any

'Unit tests for the database CLI commands.'
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from codestory.cli.client import ServiceError
from codestory.cli.commands.database import clear_database, database


@pytest.fixture
def mock_client() -> Any:
    """Mock service client."""
    client = MagicMock()
    client.clear_database.return_value = {'status': 'success', 'message': 'Database successfully cleared', 'timestamp': '2023-05-01T12:34:56Z'}
    return client

@pytest.fixture
def mock_console() -> Any:
    """Mock console."""
    return MagicMock()

@pytest.fixture
def cli_context(mock_client: Any, mock_console: Any) -> Any:
    """Click context with client and console."""
    ctx = MagicMock()
    ctx.obj = {'client': mock_client, 'console': mock_console}
    return ctx

def test_database_group() -> None:
    """Test the database command group."""
    runner = CliRunner()
    result = runner.invoke(database, ['--help'])
    assert result.exit_code == 0
    assert 'Manage the graph database' in result.output

def test_clear_database_with_force(cli_context: Any, mock_client: Any, mock_console: Any) -> None:
    """Test clearing the database with force option."""
    runner = CliRunner()
    result = runner.invoke(clear_database, ['--force'], obj=cli_context.obj)
    assert result.exit_code == 0
    mock_client.clear_database.assert_called_once_with(confirm=True)
    assert mock_console.print.call_count >= 2

def test_clear_database_error(cli_context: Any, mock_client: Any, mock_console: Any) -> None:
    """Test handling errors when clearing the database."""
    mock_client.clear_database.side_effect = ServiceError('Failed to clear database')
    runner = CliRunner()
    result = runner.invoke(clear_database, ['--force'], obj=cli_context.obj)
    assert result.exit_code == 0
    mock_client.clear_database.assert_called_once_with(confirm=True)
    error_calls = [call for call in mock_console.print.call_args_list if 'Error' in str(call)]
    assert len(error_calls) > 0