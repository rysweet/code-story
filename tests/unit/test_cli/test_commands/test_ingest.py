"""Unit tests for the ingest CLI commands."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from codestory.cli.commands import ingest
from codestory.cli.main import app


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

    def test_ingest_start(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest start' command."""
        mock_service_client.start_ingestion.return_value = {"job_id": "test-123"}
        mock_service_client.base_url = "http://localhost:8000/v1"
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "codestory.cli.commands.ingest._show_progress"
        ), patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            with patch(
                "codestory.cli.commands.ingest.setup_repository_mount",
                return_value=True,
            ), patch(
                "codestory.cli.commands.ingest.wait_for_service",
                return_value=True,
            ):
                result = cli_runner.invoke(app, ["ingest", "start", temp_dir])
            assert result.exit_code == 0
            assert "Starting ingestion" in result.output
            assert "test-123" in result.output
            mock_service_client.start_ingestion.assert_called_once()
            path_arg = mock_service_client.start_ingestion.call_args[0][0]
            repo_name = os.path.basename(os.path.abspath(temp_dir))
            expected_container_path = f"/repositories/{repo_name}"
            assert path_arg == expected_container_path

    def test_ingest_start_no_progress(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest start --no-progress' command."""
        mock_service_client.start_ingestion.return_value = {"job_id": "test-123"}
        mock_service_client.base_url = "http://localhost:8000/v1"
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "codestory.cli.commands.ingest._show_progress"
        ) as mock_show_progress:
            with patch(
                "codestory.cli.main.ServiceClient", return_value=mock_service_client
            ), patch(
                "codestory.cli.commands.ingest.setup_repository_mount",
                return_value=True,
            ), patch(
                "codestory.cli.commands.ingest.wait_for_service",
                return_value=True,
            ):
                result = cli_runner.invoke(
                    app, ["ingest", "start", temp_dir, "--no-progress"]
                )
            assert result.exit_code == 0
            assert "Starting ingestion" in result.output
            assert "test-123" in result.output
            mock_show_progress.assert_not_called()

    def test_ingest_start_error(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest start' with error."""
        mock_service_client.start_ingestion.return_value = {}
        mock_service_client.base_url = "http://localhost:8000/v1"
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "codestory.cli.main.ServiceClient", return_value=mock_service_client
            ), patch(
                "codestory.cli.commands.ingest.setup_repository_mount",
                return_value=True,
            ), patch(
                "codestory.cli.commands.ingest.wait_for_service", return_value=True
            ):
                result = cli_runner.invoke(app, ["ingest", "start", temp_dir])
            assert result.exit_code == 0
            assert "Error" in result.output

    def test_ingest_status(
        self,
        cli_runner: CliRunner,
        mock_service_client: MagicMock,
        sample_ingestion_status: dict,
    ) -> None:
        """Test 'ingest status' command."""
        # Configure mock client
        mock_service_client.get_ingestion_status.return_value = sample_ingestion_status

        # Run CLI with ingest status
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "status", "test-123"])

        # Check result
        assert result.exit_code == 0
        assert "Status" in result.output
        assert "test-123" in result.output
        assert "filesystem" in result.output
        assert "blarify" in result.output

        # Check client calls
        mock_service_client.get_ingestion_status.assert_called_once_with("test-123")

    def test_ingest_stop(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest stop' command."""
        # Configure mock client
        mock_service_client.stop_ingestion.return_value = {"success": True}

        # Run CLI with ingest stop
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "stop", "test-123"])

        # Check result
        assert result.exit_code == 0
        assert "Stopping job" in result.output
        assert "stopped" in result.output

        # Check client calls
        mock_service_client.stop_ingestion.assert_called_once_with("test-123")

    def test_ingest_stop_error(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest stop' with error."""
        # Configure mock client to return error
        mock_service_client.stop_ingestion.return_value = {
            "success": False,
            "message": "Job not found",
        }

        # Run CLI with ingest stop
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "stop", "test-123"])

        # Check result
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Job not found" in result.output

    def test_ingest_jobs(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest jobs' command."""
        # Configure mock client
        mock_service_client.list_ingestion_jobs.return_value = [
            {
                "job_id": "job-1",
                "status": "completed",
                "repository_path": "/path/1",
                "created_at": "2023-01-01",
                "progress": 100,
            },
            {
                "job_id": "job-2",
                "status": "running",
                "repository_path": "/path/2",
                "created_at": "2023-01-02",
                "progress": 50,
            },
        ]

        # Run CLI with ingest jobs
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "jobs"])

        # Check result
        assert result.exit_code == 0
        assert "Ingestion Jobs" in result.output
        assert "job-1" in result.output
        assert "job-2" in result.output
        assert "completed" in result.output.lower()
        assert "running" in result.output.lower()

        # Check client calls
        mock_service_client.list_ingestion_jobs.assert_called_once()

    def test_ingest_jobs_empty(
        self, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest jobs' with no jobs."""
        # Configure mock client to return empty list
        mock_service_client.list_ingestion_jobs.return_value = []

        # Run CLI with ingest jobs
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "jobs"])

        # Check result
        assert result.exit_code == 0
        assert "No ingestion jobs found" in result.output

    def test_is_repo_mounted(self) -> None:
        """Test the is_repo_mounted function."""
        # Mock the subprocess.run function
        with patch("subprocess.run") as mock_run:
            # Mock console
            mock_console = MagicMock()

            # Configure mock to simulate repository not mounted
            service_check = MagicMock()
            service_check.stdout = "codestory-service"  # Container is running

            directory_check = MagicMock()
            directory_check.returncode = 1  # Directory doesn't exist

            mock_run.side_effect = [service_check, directory_check]

            # Test with repository not mounted
            result = ingest.is_repo_mounted("/fake/repo", mock_console)
            assert not result

            # Reset mock
            mock_run.reset_mock()
            mock_run.side_effect = None

            # Configure mock to simulate repository mounted
            service_check = MagicMock()
            service_check.stdout = "codestory-service"  # Container is running

            directory_check = MagicMock()
            directory_check.returncode = 0  # Directory exists with content

            file_check = MagicMock()
            file_check.stdout = "exists"  # File exists in container

            mock_run.side_effect = [service_check, directory_check, file_check]

            # Test with repository mounted
            result = ingest.is_repo_mounted("/fake/repo", mock_console)
            assert result

    def test_setup_repository_mount(self) -> None:
        """Test the setup_repository_mount function."""
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the necessary functions
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
                                    # Mock console
                                    mock_console = MagicMock()

                                    # Configure mocks - Docker is running, repo is not mounted
                                    mock_docker.return_value = True
                                    mock_mounted.return_value = False
                                    mock_create_file.return_value = True
                                    mock_run.return_value = True
                                    mock_wait.return_value = True
                                    mock_config.return_value = True

                                    # Test normal case
                                    result = ingest.setup_repository_mount(
                                        temp_dir, mock_console
                                    )
                                    assert result

                                    # Check function calls
                                    mock_docker.assert_called_once()
                                    mock_create_file.assert_called_once()
                                    mock_run.assert_called_once()
                                    mock_wait.assert_called_once()
                                    mock_config.assert_called_once()

                                    # Reset mocks
                                    mock_docker.reset_mock()
                                    mock_mounted.reset_mock()
                                    mock_create_file.reset_mock()
                                    mock_run.reset_mock()
                                    mock_wait.reset_mock()
                                    mock_config.reset_mock()

                                    # Configure mocks - Docker is running, repo is already mounted
                                    mock_docker.return_value = True
                                    mock_mounted.return_value = True

                                    # Test when repo is already mounted
                                    result = ingest.setup_repository_mount(
                                        temp_dir, mock_console
                                    )
                                    assert result

                                    # Check function calls - should exit early
                                    mock_mounted.assert_called_once()
                                    mock_create_file.assert_not_called()

    def test_ingest_mount_command(self, cli_runner: CliRunner) -> None:
        """Test the 'ingest mount' command."""
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the repository mounting function
            with patch(
                "codestory.cli.commands.ingest.setup_repository_mount"
            ) as mock_setup:
                # Configure mock to return success
                mock_setup.return_value = True

                # Run CLI with ingest mount
                result = cli_runner.invoke(app, ["ingest", "mount", temp_dir])

                # Check result
                assert result.exit_code == 0
                assert "mount" in result.output.lower()
                assert "Successfully mounted" in result.output

                # Check function calls
                mock_setup.assert_called_once()

                # Reset mock
                mock_setup.reset_mock()

                # Configure mock to return failure
                mock_setup.return_value = False

                # Run CLI with ingest mount
                result = cli_runner.invoke(app, ["ingest", "mount", temp_dir])

                # Check result
                assert result.exit_code == 0
                assert "Failed to mount" in result.output
