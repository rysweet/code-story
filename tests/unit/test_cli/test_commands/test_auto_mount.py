"""
Unit tests for auto-mount functionality in the ingest command.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock
import subprocess

import pytest
from click.testing import CliRunner
from rich.console import Console

from codestory.cli.commands.ingest import ingest, start_ingestion
from codestory.cli.client.service_client import ServiceClient


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


class TestAutoMount:
    """Tests for auto-mount functionality in the ingest command."""

    def test_container_detection(self, cli_runner, cli_context):
        """Test that Docker container deployment is detected correctly."""
        # Create temporary repository path
        with tempfile.TemporaryDirectory() as repo_path:
            # Set up mocks
            cli_context["client"].base_url = "http://localhost:8000/v1"
            
            # Mock subprocess calls
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = "codestory-service"
                mock_run.return_value.returncode = 0
                
                # Create CLI runner and call the command
                runner = cli_runner
                runner.isolation_level = "none"  # Needed to access mocks inside command
                
                with patch("codestory.cli.commands.ingest.os.path.exists") as mock_exists:
                    # Mock auto_mount.py script does not exist
                    mock_exists.return_value = False
                    
                    # Invoke the command
                    with patch.object(cli_context["client"], "start_ingestion") as mock_start:
                        mock_start.return_value = {"job_id": "test-job-id"}
                        
                        # Mock command context
                        with patch("click.get_current_context") as mock_context:
                            mock_context.return_value.obj = cli_context
                            
                            # Call the command directly to bypass CLI validation
                            start_ingestion.callback(
                                cli_context,
                                repo_path,
                                no_progress=True,
                                container=False,
                                path_prefix="/repositories",
                                auto_mount=True,
                                no_auto_mount=False,
                            )
                            
                            # Verify that container path was passed to start_ingestion
                            args, kwargs = mock_start.call_args
                            assert kwargs == {}
                            assert "/repositories" in args[0]
                            assert os.path.basename(repo_path) in args[0]

    def test_auto_mount_execution(self, cli_runner, cli_context):
        """Test that auto_mount.py is executed when repository is not mounted."""
        # Create temporary repository path
        with tempfile.TemporaryDirectory() as repo_path:
            # Set up mocks
            cli_context["client"].base_url = "http://localhost:8000/v1"
            
            # Mock subprocess calls
            with patch("subprocess.run") as mock_run:
                # First call: check if Docker is running
                mock_run.side_effect = [
                    MagicMock(stdout="codestory-service", returncode=0),
                    # Second call: check if path exists in container (it doesn't)
                    MagicMock(stdout="", returncode=1),
                    # Third call: execute auto_mount.py
                    MagicMock(returncode=0),
                ]
                
                # Create CLI runner and call the command
                runner = cli_runner
                runner.isolation_level = "none"  # Needed to access mocks inside command
                
                # Path to auto_mount.py
                script_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
                    "scripts", "auto_mount.py"
                )
                
                with patch("codestory.cli.commands.ingest.os.path.exists") as mock_exists:
                    # Mock auto_mount.py script exists
                    mock_exists.return_value = True
                    
                    with patch("sys.executable", new="python"):
                        # Invoke the command
                        with patch.object(cli_context["client"], "start_ingestion") as mock_start:
                            mock_start.return_value = {"job_id": "test-job-id"}
                            
                            # Mock command context
                            with patch("click.get_current_context") as mock_context:
                                mock_context.return_value.obj = cli_context
                                
                                # Call the command directly to bypass CLI validation
                                start_ingestion.callback(
                                    cli_context,
                                    repo_path,
                                    no_progress=True,
                                    container=False,
                                    path_prefix="/repositories",
                                    auto_mount=True,
                                    no_auto_mount=False,
                                )
                                
                                # Verify auto_mount.py was called
                                auto_mount_call = [call for call in mock_run.call_args_list 
                                                if "auto_mount.py" in str(call)]
                                
                                assert len(auto_mount_call) >= 1
                                
                                # Verify that container path was passed to start_ingestion
                                args, kwargs = mock_start.call_args
                                assert kwargs == {}
                                assert "/repositories" in args[0]
                                assert os.path.basename(repo_path) in args[0]

    def test_no_auto_mount(self, cli_runner, cli_context):
        """Test that --no-auto-mount flag disables auto mounting."""
        # Create temporary repository path
        with tempfile.TemporaryDirectory() as repo_path:
            # Set up mocks
            cli_context["client"].base_url = "http://localhost:8000/v1"
            
            # Create CLI runner and call the command
            runner = cli_runner
            runner.isolation_level = "none"  # Needed to access mocks inside command
            
            with patch("subprocess.run") as mock_run:
                # Invoke the command
                with patch.object(cli_context["client"], "start_ingestion") as mock_start:
                    mock_start.return_value = {"job_id": "test-job-id"}
                    
                    # Mock command context
                    with patch("click.get_current_context") as mock_context:
                        mock_context.return_value.obj = cli_context
                        
                        # Call the command directly to bypass CLI validation
                        start_ingestion.callback(
                            cli_context,
                            repo_path,
                            no_progress=True,
                            container=False,
                            path_prefix="/repositories",
                            auto_mount=True,
                            no_auto_mount=True,  # Disable auto-mount
                        )
                        
                        # Verify that subprocess.run was not called for auto-mount
                        assert mock_run.call_count == 0
                        
                        # Verify that correct path was passed to start_ingestion
                        args, kwargs = mock_start.call_args
                        assert kwargs == {}
                        assert "/repositories" in args[0]
                        assert os.path.basename(repo_path) in args[0]

    def test_non_docker_deployment(self, cli_runner, cli_context):
        """Test behavior with non-Docker deployment."""
        # Create temporary repository path
        with tempfile.TemporaryDirectory() as repo_path:
            # Set up mocks for non-Docker deployment
            cli_context["client"].base_url = "https://remote-server.com/v1"
            
            # Create CLI runner and call the command
            runner = cli_runner
            runner.isolation_level = "none"  # Needed to access mocks inside command
            
            with patch("subprocess.run") as mock_run:
                # Invoke the command
                with patch.object(cli_context["client"], "start_ingestion") as mock_start:
                    mock_start.return_value = {"job_id": "test-job-id"}
                    
                    # Mock command context
                    with patch("click.get_current_context") as mock_context:
                        mock_context.return_value.obj = cli_context
                        
                        # Call the command directly to bypass CLI validation
                        start_ingestion.callback(
                            cli_context,
                            repo_path,
                            no_progress=True,
                            container=False,
                            path_prefix="/repositories",
                            auto_mount=True,
                            no_auto_mount=False,
                        )
                        
                        # Verify that subprocess.run was not called
                        assert mock_run.call_count == 0
                        
                        # Verify that local path was passed to start_ingestion (not container path)
                        args, kwargs = mock_start.call_args
                        assert kwargs == {}
                        assert repo_path in args[0]
                        assert "/repositories" not in args[0]


class TestAutoMountFlags:
    """Tests for auto-mount related CLI flags."""

    def test_auto_mount_flag(self, cli_runner, cli_context):
        """Test that --auto-mount flag works as expected."""
        # Create temporary repository path
        with tempfile.TemporaryDirectory() as repo_path:
            # Set up mocks
            cli_context["client"].base_url = "http://localhost:8000/v1"
            
            # Create CLI runner and call the command
            runner = cli_runner
            runner.isolation_level = "none"  # Needed to access mocks inside command
            
            with patch("subprocess.run") as mock_run:
                # Invoke the command
                with patch.object(cli_context["client"], "start_ingestion") as mock_start:
                    mock_start.return_value = {"job_id": "test-job-id"}
                    
                    # Mock command context
                    with patch("click.get_current_context") as mock_context:
                        mock_context.return_value.obj = cli_context
                        
                        # Call via CLI runner for flag testing
                        with patch("codestory.cli.commands.ingest.start_ingestion.callback") as mock_callback:
                            # Mock run CLI command with --auto-mount flag
                            result = runner.invoke(ingest, ["start", repo_path, "--auto-mount"])
                            
                            # Extract the arguments passed to the callback
                            args, kwargs = mock_callback.call_args
                            
                            # Verify that auto_mount=True was passed
                            assert kwargs["auto_mount"] is True
                            assert kwargs["no_auto_mount"] is False

    def test_no_auto_mount_flag(self, cli_runner, cli_context):
        """Test that --no-auto-mount flag works as expected."""
        # Create temporary repository path
        with tempfile.TemporaryDirectory() as repo_path:
            # Set up mocks
            cli_context["client"].base_url = "http://localhost:8000/v1"
            
            # Create CLI runner and call the command
            runner = cli_runner
            runner.isolation_level = "none"  # Needed to access mocks inside command
            
            with patch("subprocess.run") as mock_run:
                # Invoke the command
                with patch.object(cli_context["client"], "start_ingestion") as mock_start:
                    mock_start.return_value = {"job_id": "test-job-id"}
                    
                    # Mock command context
                    with patch("click.get_current_context") as mock_context:
                        mock_context.return_value.obj = cli_context
                        
                        # Call via CLI runner for flag testing
                        with patch("codestory.cli.commands.ingest.start_ingestion.callback") as mock_callback:
                            # Mock run CLI command with --no-auto-mount flag
                            result = runner.invoke(ingest, ["start", repo_path, "--no-auto-mount"])
                            
                            # Extract the arguments passed to the callback
                            args, kwargs = mock_callback.call_args
                            
                            # Verify that no_auto_mount=True was passed
                            assert kwargs["no_auto_mount"] is True