"""Unit tests for the ingest CLI commands."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from codestory.cli.main import app
from codestory.cli.client import ServiceError


class TestIngestCommands:
    """Tests for the ingest CLI commands."""
    
    def test_ingest_help(self, cli_runner: CliRunner) -> None:
        """Test 'ingest --help' command."""
        # Run CLI with ingest --help
        result = cli_runner.invoke(app, ["ingest", "--help"])
        
        # Check result
        assert result.exit_code == 0
        assert "ingest" in result.output.lower()
        assert "start" in result.output.lower()
        assert "status" in result.output.lower()
        assert "stop" in result.output.lower()
        assert "jobs" in result.output.lower()
    
    def test_ingest_start(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'ingest start' command."""
        # Configure mock client
        mock_service_client.start_ingestion.return_value = {"job_id": "test-123"}
        
        # Create temporary directory for test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the _show_progress function to avoid actually showing progress
            with patch("codestory.cli.commands.ingest._show_progress") as mock_show_progress:
                # Mock the ServiceClient creation
                with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                    # Run CLI with ingest start
                    result = cli_runner.invoke(
                        app,
                        ["ingest", "start", temp_dir]
                    )

                    # Check result
                    assert result.exit_code == 0
                    assert "Starting ingestion" in result.output
                    assert "test-123" in result.output

                    # Check client calls
                    mock_service_client.start_ingestion.assert_called_once()
                    path_arg = mock_service_client.start_ingestion.call_args[0][0]
                    assert os.path.abspath(temp_dir) == path_arg
    
    def test_ingest_start_no_progress(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'ingest start --no-progress' command."""
        # Configure mock client
        mock_service_client.start_ingestion.return_value = {"job_id": "test-123"}
        
        # Create temporary directory for test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run CLI with ingest start --no-progress
            with patch("codestory.cli.commands.ingest._show_progress") as mock_show_progress:
                with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                    result = cli_runner.invoke(
                        app,
                        ["ingest", "start", temp_dir, "--no-progress"]
                    )
                
                # Check result
                assert result.exit_code == 0
                assert "Starting ingestion" in result.output
                assert "test-123" in result.output
                
                # Check progress tracking not called
                mock_show_progress.assert_not_called()
    
    def test_ingest_start_error(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'ingest start' with error."""
        # Configure mock client to return error
        mock_service_client.start_ingestion.return_value = {}
        
        # Create temporary directory for test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run CLI with ingest start
            with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
                result = cli_runner.invoke(
                    app,
                    ["ingest", "start", temp_dir]
                )
            
            # Check result
            assert result.exit_code == 0
            assert "Error" in result.output
    
    def test_ingest_status(self, cli_runner: CliRunner, mock_service_client: MagicMock, sample_ingestion_status: dict) -> None:
        """Test 'ingest status' command."""
        # Configure mock client
        mock_service_client.get_ingestion_status.return_value = sample_ingestion_status
        
        # Run CLI with ingest status
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(
                app,
                ["ingest", "status", "test-123"]
            )
        
        # Check result
        assert result.exit_code == 0
        assert "Status" in result.output
        assert "test-123" in result.output
        assert "filesystem" in result.output
        assert "blarify" in result.output
        
        # Check client calls
        mock_service_client.get_ingestion_status.assert_called_once_with("test-123")
    
    def test_ingest_stop(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'ingest stop' command."""
        # Configure mock client
        mock_service_client.stop_ingestion.return_value = {"success": True}
        
        # Run CLI with ingest stop
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(
                app,
                ["ingest", "stop", "test-123"]
            )
        
        # Check result
        assert result.exit_code == 0
        assert "Stopping job" in result.output
        assert "stopped" in result.output
        
        # Check client calls
        mock_service_client.stop_ingestion.assert_called_once_with("test-123")
    
    def test_ingest_stop_error(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'ingest stop' with error."""
        # Configure mock client to return error
        mock_service_client.stop_ingestion.return_value = {
            "success": False, 
            "message": "Job not found"
        }
        
        # Run CLI with ingest stop
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(
                app,
                ["ingest", "stop", "test-123"]
            )
        
        # Check result
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Job not found" in result.output
    
    def test_ingest_jobs(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'ingest jobs' command."""
        # Configure mock client
        mock_service_client.list_ingestion_jobs.return_value = [
            {
                "job_id": "job-1", 
                "status": "completed", 
                "repository_path": "/path/1",
                "created_at": "2023-01-01", 
                "progress": 100
            },
            {
                "job_id": "job-2", 
                "status": "running", 
                "repository_path": "/path/2",
                "created_at": "2023-01-02", 
                "progress": 50
            },
        ]
        
        # Run CLI with ingest jobs
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(
                app,
                ["ingest", "jobs"]
            )
        
        # Check result
        assert result.exit_code == 0
        assert "Ingestion Jobs" in result.output
        assert "job-1" in result.output
        assert "job-2" in result.output
        assert "completed" in result.output.lower()
        assert "running" in result.output.lower()
        
        # Check client calls
        mock_service_client.list_ingestion_jobs.assert_called_once()
    
    def test_ingest_jobs_empty(self, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'ingest jobs' with no jobs."""
        # Configure mock client to return empty list
        mock_service_client.list_ingestion_jobs.return_value = []
        
        # Run CLI with ingest jobs
        with patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            result = cli_runner.invoke(
                app,
                ["ingest", "jobs"]
            )
        
        # Check result
        assert result.exit_code == 0
        assert "No ingestion jobs found" in result.output