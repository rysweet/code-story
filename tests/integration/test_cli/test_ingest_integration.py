"""Integration tests for CLI ingestion commands."""

import os
import tempfile
import time
from typing import Any

import pytest
from click.testing import CliRunner

from codestory.cli.commands.ingest import is_docker_running, is_repo_mounted
from codestory.cli.main import app


class TestIngestCommands:
    """Integration tests for ingestion-related CLI commands."""

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_ingest_start_and_status(
        self,
        cli_runner: CliRunner,
        running_service: dict[str, Any],
        test_repository: str,
    ) -> None:
        """Test 'ingest start' and 'ingest status' commands with real repository."""
        # Start ingestion
        result = cli_runner.invoke(
            app, ["ingest", "start", test_repository, "--no-progress"]
        )

        # Check result
        assert result.exit_code == 0
        assert "Starting ingestion" in result.output

        # Extract job ID from output
        job_id_line = [
            line for line in result.output.splitlines() if "Job ID:" in line
        ][0]
        job_id = job_id_line.split("Job ID:")[1].strip()
        assert job_id

        # Wait a moment for the job to start
        time.sleep(1)

        # Check status
        status_result = cli_runner.invoke(app, ["ingest", "status", job_id])

        # Check result
        assert status_result.exit_code == 0
        assert job_id in status_result.output

        # The status should show at least one step (e.g., "filesystem")
        assert (
            "filesystem" in status_result.output.lower()
            or "running" in status_result.output.lower()
        )

    @pytest.mark.integration
    def test_ingest_start_command_format(self, cli_runner: CliRunner) -> None:
        """Test that 'ingest start' uses positional arguments correctly."""
        # Test with incorrect option format
        invalid_result = cli_runner.invoke(app, ["ingest", "start", "--path", "."])

        # Should fail with an error about unrecognized option
        assert invalid_result.exit_code != 0
        assert "Error: No such option: --path" in invalid_result.output

        # The correct format (with positional arg) should parse correctly
        # We're not actually running the ingestion, just checking the command parsing
        help_result = cli_runner.invoke(app, ["ingest", "start", "--help"])
        assert help_result.exit_code == 0
        assert "Usage: app ingest start [OPTIONS] REPOSITORY_PATH" in help_result.output
        assert (
            "REPOSITORY_PATH is the path to the repository to ingest"
            in help_result.output
        )

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_ingest_jobs_list(
        self, cli_runner: CliRunner, running_service: dict[str, Any]
    ) -> None:
        """Test 'ingest jobs' command with real service."""
        # List all jobs
        result = cli_runner.invoke(app, ["ingest", "jobs"])

        # Check result
        assert result.exit_code == 0

        # Should either have jobs or indicate no jobs
        assert (
            "Ingestion Jobs" in result.output
            or "No ingestion jobs found" in result.output
        )

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_mount_command(
        self, cli_runner: CliRunner, running_service: dict[str, Any]
    ) -> None:
        """Test the 'ingest mount' command with a real repository."""
        # Only run this test if Docker is available
        if not is_docker_running():
            pytest.skip("Docker is not running, skipping test")

        # Create a temporary test repository
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple file to verify the mount
            with open(os.path.join(temp_dir, "test.txt"), "w") as f:
                f.write("test content")

            # Run the mount command
            result = cli_runner.invoke(
                app, ["ingest", "mount", temp_dir, "--debug"], catch_exceptions=False
            )

            # Check the result
            assert result.exit_code == 0

            # The output should either indicate success or that it's already mounted
            assert (
                "Successfully mounted" in result.output
                or "already mounted" in result.output
            )

            # Verify that the repository is actually mounted
            assert is_repo_mounted(temp_dir)

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_force_remount(
        self, cli_runner: CliRunner, running_service: dict[str, Any]
    ) -> None:
        """Test the '--force-remount' option with a real repository."""
        # Only run this test if Docker is available
        if not is_docker_running():
            pytest.skip("Docker is not running, skipping test")

        # Create a temporary test repository
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple file to verify the mount
            with open(os.path.join(temp_dir, "test.txt"), "w") as f:
                f.write("test content")

            # First mount the repository normally
            cli_runner.invoke(app, ["ingest", "mount", temp_dir])

            # Then force remount
            result = cli_runner.invoke(
                app,
                ["ingest", "mount", temp_dir, "--force-remount"],
                catch_exceptions=False,
            )

            # Check the result
            assert result.exit_code == 0

            # Should indicate successful mount
            assert "Successfully mounted" in result.output

            # Verify that the repository is actually mounted
            assert is_repo_mounted(temp_dir)
