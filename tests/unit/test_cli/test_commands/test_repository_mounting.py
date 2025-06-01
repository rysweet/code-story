from typing import Any

"\nUnit tests for repository mounting functionality in the ingest command.\n"
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from codestory.cli.client.service_client import ServiceClient
from codestory.cli.commands import ingest


@pytest.fixture
def mock_client() -> Any:
    """Mock ServiceClient for testing."""
    client = MagicMock(spec=ServiceClient)
    client.base_url = "http://localhost:8000"
    return client


@pytest.fixture
def cli_context() -> Any:
    """Mock CLI context for testing."""
    console = Console(file=MagicMock())
    settings = MagicMock()
    return {
        "client": MagicMock(spec=ServiceClient),
        "console": console,
        "settings": settings,
    }


class TestRepositoryMounting:
    """Tests for repository mounting functionality in the ingest command."""

    def test_is_repo_mounted(self: Any) -> None:
        """Test the is_repo_mounted function."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="codestory-service", returncode=0),
                MagicMock(returncode=1),
            ]
            result = ingest.is_repo_mounted("/test/repo", console=None)
            assert result is False
            mock_run.reset_mock()
            mock_run.side_effect = [
                MagicMock(stdout="codestory-service", returncode=0),
                MagicMock(returncode=0),
                MagicMock(stdout="exists", returncode=0),
            ]
            with patch("os.path.exists", return_value=True):
                result = ingest.is_repo_mounted("/test/repo", console=None)
                assert result is True

    def test_setup_repository_mount(self: Any) -> None:
        """Test the setup_repository_mount function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "codestory.cli.commands.ingest.is_docker_running"
            ) as mock_docker:
                with patch(
                    "codestory.cli.commands.ingest.is_repo_mounted"
                ) as mock_mounted:
                    with patch(
                        "codestory.cli.commands.ingest.create_override_file"
                    ) as mock_create_file:
                        with patch(
                            "codestory.cli.commands.ingest.run_command"
                        ) as mock_run:
                            with patch(
                                "codestory.cli.commands.ingest.wait_for_service"
                            ) as mock_wait:
                                with patch(
                                    "codestory.cli.commands.ingest.create_repo_config"
                                ) as mock_config:
                                    console = MagicMock()
                                    mock_docker.return_value = True
                                    mock_mounted.return_value = True
                                    result = ingest.setup_repository_mount(
                                        temp_dir, console
                                    )
                                    assert result is True
                                    mock_docker.assert_called_once()
                                    mock_mounted.assert_called_once()
                                    mock_create_file.assert_not_called()
                                    mock_run.assert_not_called()
                                    mock_docker.reset_mock()
                                    mock_mounted.reset_mock()
                                    mock_create_file.reset_mock()
                                    mock_run.reset_mock()
                                    mock_wait.reset_mock()
                                    mock_config.reset_mock()
                                    mock_docker.return_value = True
                                    mock_mounted.return_value = False
                                    mock_create_file.return_value = True
                                    mock_wait.return_value = True
                                    mock_config.return_value = True
                                    mock_mounted.side_effect = [False, True]
                                    result = ingest.setup_repository_mount(
                                        temp_dir, console
                                    )
                                    assert result is True
                                    mock_docker.assert_called_once()
                                    assert mock_mounted.call_count == 2
                                    mock_create_file.assert_called_once()
                                    mock_run.assert_called_once()
                                    mock_wait.assert_called_once()
                                    mock_config.assert_called_once()

    def test_create_override_file(self: Any) -> None:
        """Test the create_override_file function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_open = MagicMock()
            with patch("builtins.open", mock_open):
                console = MagicMock()
                result = ingest.create_override_file(temp_dir, console)
                assert result is True
                mock_open.assert_called_once()
                write_call = mock_open.return_value.__enter__.return_value.write
                write_call.assert_called_once()
                content = write_call.call_args[0][0]
                assert temp_dir in content
                assert "services:" in content
                assert "service:" in content
                assert "worker:" in content
                assert "volumes:" in content
