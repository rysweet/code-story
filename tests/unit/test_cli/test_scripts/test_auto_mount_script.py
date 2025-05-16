"""
Unit tests for the auto_mount.py script.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock
import subprocess
import time

import pytest

# Import the auto_mount module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(__file__))))), "scripts"))
import auto_mount


class TestAutoMountScript:
    """Tests for auto_mount.py script."""

    def test_is_docker_running(self):
        """Test detection of running Docker containers."""
        with patch("subprocess.run") as mock_run:
            # Test when Docker is running
            mock_run.return_value = MagicMock(
                stdout="codestory-service",
                returncode=0
            )
            assert auto_mount.is_docker_running() is True
            
            # Test when Docker is not running
            mock_run.return_value = MagicMock(
                stdout="",
                returncode=0
            )
            assert auto_mount.is_docker_running() is False
            
            # Test when command fails
            mock_run.side_effect = Exception("Test exception")
            assert auto_mount.is_docker_running() is False

    def test_get_current_mounts(self):
        """Test getting current mounts from Docker containers."""
        with patch("subprocess.run") as mock_run:
            # Test successful response
            mock_run.return_value = MagicMock(
                stdout='[{"Source":"/path/to/repo","Destination":"/repositories/repo"}]',
                returncode=0
            )
            result = auto_mount.get_current_mounts()
            assert "/path/to/repo" in result
            assert "/repositories/repo" in result
            
            # Test command failure
            mock_run.side_effect = Exception("Test exception")
            assert auto_mount.get_current_mounts() == ""

    def test_is_repo_mounted(self):
        """Test checking if repository is already mounted."""
        with patch("auto_mount.get_current_mounts") as mock_get_mounts:
            # Test when repository is mounted
            mock_get_mounts.return_value = '[{"Source":"/path/to/repo","Destination":"/repositories/repo"}]'
            assert auto_mount.is_repo_mounted("/path/to/repo") is True
            
            # Test when repository is not mounted
            assert auto_mount.is_repo_mounted("/different/path") is False

    def test_create_repo_config(self):
        """Test creating repository configuration file."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create repository config
            auto_mount.create_repo_config(temp_dir)
            
            # Check if config file was created
            config_path = os.path.join(temp_dir, ".codestory", "repository.toml")
            assert os.path.exists(config_path)
            
            # Check config file contents
            with open(config_path, "r") as f:
                config = f.read()
                assert "[repository]" in config
                assert f'name = "{os.path.basename(temp_dir)}"' in config
                assert f'local_path = "{temp_dir}"' in config
                assert f'container_path = "/repositories/{os.path.basename(temp_dir)}"' in config
                assert "auto_mounted = true" in config

    @patch("auto_mount.run_command")
    @patch("auto_mount.is_docker_running")
    @patch("auto_mount.is_repo_mounted")
    @patch("auto_mount.create_repo_config")
    def test_setup_repository_mount_already_mounted(
        self, mock_create_config, mock_is_mounted, mock_is_docker, mock_run_command
    ):
        """Test setup_repository_mount when repository is already mounted."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock Docker running and repository already mounted
            mock_is_docker.return_value = True
            mock_is_mounted.return_value = True
            
            # Call setup_repository_mount
            result = auto_mount.setup_repository_mount(temp_dir)
            
            # Verify result
            assert result is True
            
            # Verify create_repo_config was not called
            mock_create_config.assert_not_called()
            
            # Verify run_command was not called to restart containers
            assert mock_run_command.call_count == 0

    @patch("auto_mount.run_command")
    @patch("auto_mount.is_docker_running")
    @patch("auto_mount.is_repo_mounted")
    @patch("auto_mount.create_repo_config")
    @patch("auto_mount.wait_for_service")
    def test_setup_repository_mount_needs_mounting(
        self, mock_wait, mock_create_config, mock_is_mounted, mock_is_docker, mock_run_command
    ):
        """Test setup_repository_mount when repository needs to be mounted."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock Docker running but repository not mounted
            mock_is_docker.return_value = True
            mock_is_mounted.return_value = False
            mock_wait.return_value = True
            
            # Call setup_repository_mount
            result = auto_mount.setup_repository_mount(temp_dir)
            
            # Verify result
            assert result is True
            
            # Verify create_repo_config was called
            mock_create_config.assert_called_once_with(temp_dir)
            
            # Verify run_command was called to stop and start containers
            assert mock_run_command.call_count == 2
            assert "down" in str(mock_run_command.call_args_list[0])
            assert "up -d" in str(mock_run_command.call_args_list[1])
            
            # Verify wait_for_service was called
            mock_wait.assert_called_once()

    @patch("auto_mount.run_command")
    @patch("auto_mount.time.sleep", return_value=None)
    def test_wait_for_service(self, mock_sleep, mock_run_command):
        """Test wait_for_service function."""
        # Mock subprocess run to check service health
        with patch("subprocess.run") as mock_run:
            # Test when service becomes healthy immediately
            mock_run.return_value = MagicMock(stdout="healthy", returncode=0)
            result = auto_mount.wait_for_service()
            assert result is True
            assert mock_sleep.call_count == 0
            
            # Reset mocks
            mock_sleep.reset_mock()
            
            # Test when service becomes healthy after a few attempts
            mock_run.side_effect = [
                MagicMock(stdout="starting", returncode=0),
                MagicMock(stdout="starting", returncode=0),
                MagicMock(stdout="healthy", returncode=0),
            ]
            result = auto_mount.wait_for_service()
            assert result is True
            assert mock_sleep.call_count == 2
            
            # Reset mocks
            mock_sleep.reset_mock()
            mock_run.reset_mock()
            
            # Test when service never becomes healthy
            mock_run.return_value = MagicMock(stdout="starting", returncode=0)
            # Reduce max_attempts to speed up test
            with patch("auto_mount.wait_for_service.__defaults__", (3,)):
                result = auto_mount.wait_for_service()
                assert result is False
                assert mock_sleep.call_count == 3

    @patch("auto_mount.setup_repository_mount")
    @patch("auto_mount.ingest_repository")
    def test_main_function(self, mock_ingest, mock_setup):
        """Test main function with different arguments."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock command-line arguments
            with patch("sys.argv", ["auto_mount.py", temp_dir]):
                # Mock setup_repository_mount to succeed
                mock_setup.return_value = True
                
                # Call main function
                with patch("auto_mount.argparse.ArgumentParser.parse_args") as mock_parse_args:
                    mock_parse_args.return_value = MagicMock(
                        repository_path=temp_dir,
                        no_progress=False,
                        no_ingest=False
                    )
                    auto_mount.main()
                    
                    # Verify setup_repository_mount was called
                    mock_setup.assert_called_once_with(temp_dir)
                    
                    # Verify ingest_repository was called
                    mock_ingest.assert_called_once_with(temp_dir, False)
                    
            # Reset mocks
            mock_setup.reset_mock()
            mock_ingest.reset_mock()
            
            # Test with --no-ingest flag
            with patch("sys.argv", ["auto_mount.py", temp_dir, "--no-ingest"]):
                # Mock setup_repository_mount to succeed
                mock_setup.return_value = True
                
                # Call main function
                with patch("auto_mount.argparse.ArgumentParser.parse_args") as mock_parse_args:
                    mock_parse_args.return_value = MagicMock(
                        repository_path=temp_dir,
                        no_progress=False,
                        no_ingest=True
                    )
                    auto_mount.main()
                    
                    # Verify setup_repository_mount was called
                    mock_setup.assert_called_once_with(temp_dir)
                    
                    # Verify ingest_repository was not called
                    mock_ingest.assert_not_called()
                    
            # Reset mocks
            mock_setup.reset_mock()
            mock_ingest.reset_mock()
            
            # Test with --no-progress flag
            with patch("sys.argv", ["auto_mount.py", temp_dir, "--no-progress"]):
                # Mock setup_repository_mount to succeed
                mock_setup.return_value = True
                
                # Call main function
                with patch("auto_mount.argparse.ArgumentParser.parse_args") as mock_parse_args:
                    mock_parse_args.return_value = MagicMock(
                        repository_path=temp_dir,
                        no_progress=True,
                        no_ingest=False
                    )
                    auto_mount.main()
                    
                    # Verify setup_repository_mount was called
                    mock_setup.assert_called_once_with(temp_dir)
                    
                    # Verify ingest_repository was called with no_progress=True
                    mock_ingest.assert_called_once_with(temp_dir, True)