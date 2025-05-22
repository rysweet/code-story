"""
Unit tests for repository mounting functionality in the ingest command.
"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from codestory.cli.client.service_client import ServiceClient
from codestory.cli.commands import ingest


@pytest.fixture
def mock_client():
    """Mock ServiceClient for testing."""
    client = MagicMock(spec=ServiceClient)
    client.base_url = "http://localhost:8000"
    return client


@pytest.fixture
def cli_context():
    """Mock CLI context for testing."""
    console = Console(file=MagicMock())
    settings = MagicMock()
    
    # Create context object with client and console
    return {
        "client": MagicMock(spec=ServiceClient),
        "console": console,
        "settings": settings,
    }


class TestRepositoryMounting:
    """Tests for repository mounting functionality in the ingest command."""

    def test_is_repo_mounted(self):
        """Test the is_repo_mounted function."""
        # Create mock for subprocess.run
        with patch("subprocess.run") as mock_run:
            # Test when repository is not mounted
            mock_run.side_effect = [
                # First call: Check if service is running
                MagicMock(stdout="codestory-service", returncode=0),
                # Second call: Check if directory exists
                MagicMock(returncode=1)
            ]
            
            # Call is_repo_mounted
            result = ingest.is_repo_mounted("/test/repo", console=None)
            
            # Verify result
            assert result is False
            
            # Reset mock
            mock_run.reset_mock()
            
            # Test when repository is mounted
            mock_run.side_effect = [
                # First call: Check if service is running
                MagicMock(stdout="codestory-service", returncode=0),
                # Second call: Check if directory exists
                MagicMock(returncode=0),
                # Third call: Check if file exists
                MagicMock(stdout="exists", returncode=0)
            ]
            
            with patch("os.path.exists", return_value=True):
                # Call is_repo_mounted
                result = ingest.is_repo_mounted("/test/repo", console=None)
                
                # Verify result
                assert result is True

    def test_setup_repository_mount(self):
        """Test the setup_repository_mount function."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mocks
            with patch("codestory.cli.commands.ingest.is_docker_running") as mock_docker:
                with patch("codestory.cli.commands.ingest.is_repo_mounted") as mock_mounted:
                    with patch("codestory.cli.commands.ingest.create_override_file") as mock_create_file:
                        with patch("codestory.cli.commands.ingest.run_command") as mock_run:
                            with patch("codestory.cli.commands.ingest.wait_for_service") as mock_wait:
                                with patch("codestory.cli.commands.ingest.create_repo_config") as mock_config:
                                    console = MagicMock()
                                    
                                    # Test when repository is already mounted
                                    mock_docker.return_value = True
                                    mock_mounted.return_value = True
                                    
                                    # Call setup_repository_mount
                                    result = ingest.setup_repository_mount(temp_dir, console)
                                    
                                    # Verify result
                                    assert result is True
                                    
                                    # Verify correct functions were called
                                    mock_docker.assert_called_once()
                                    mock_mounted.assert_called_once()
                                    mock_create_file.assert_not_called()
                                    mock_run.assert_not_called()
                                    
                                    # Reset mocks
                                    mock_docker.reset_mock()
                                    mock_mounted.reset_mock()
                                    mock_create_file.reset_mock()
                                    mock_run.reset_mock()
                                    mock_wait.reset_mock()
                                    mock_config.reset_mock()
                                    
                                    # Test when repository needs to be mounted
                                    mock_docker.return_value = True
                                    mock_mounted.return_value = False
                                    mock_create_file.return_value = True
                                    mock_wait.return_value = True
                                    mock_config.return_value = True
                                    
                                    # Mock is_repo_mounted to return False first, then True for verification
                                    mock_mounted.side_effect = [False, True]
                                    
                                    # Call setup_repository_mount
                                    result = ingest.setup_repository_mount(temp_dir, console)
                                    
                                    # Verify result
                                    assert result is True
                                    
                                    # Verify correct functions were called
                                    mock_docker.assert_called_once()
                                    assert mock_mounted.call_count == 2
                                    mock_create_file.assert_called_once()
                                    mock_run.assert_called_once()
                                    mock_wait.assert_called_once()
                                    mock_config.assert_called_once()

    def test_create_override_file(self):
        """Test the create_override_file function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock open function
            mock_open = MagicMock()
            with patch("builtins.open", mock_open):
                console = MagicMock()
                
                # Call create_override_file
                result = ingest.create_override_file(temp_dir, console)
                
                # Verify result
                assert result is True
                
                # Verify open was called
                mock_open.assert_called_once()
                
                # Verify correct content
                write_call = mock_open.return_value.__enter__.return_value.write
                write_call.assert_called_once()
                content = write_call.call_args[0][0]
                
                # Check content contains the repository path
                assert temp_dir in content
                assert "services:" in content
                assert "service:" in content
                assert "worker:" in content
                assert "volumes:" in content