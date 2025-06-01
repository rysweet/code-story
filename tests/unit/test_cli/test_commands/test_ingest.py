from typing import Any

"Unit tests for the ingest CLI commands."
import os
import tempfile
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from codestory.cli.commands import ingest
from codestory.cli.main import app


class TestIngestCommands:
    """Tests for the ingest CLI commands."""

    def test_ingest_help(self: Any, cli_runner: CliRunner) -> None:
        """Test 'ingest --help' command."""
        result = cli_runner.invoke(app, ["ingest", "--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output.lower()
        assert "start" in result.output.lower()
        assert "status" in result.output.lower()
        assert "stop" in result.output.lower()
        assert "jobs" in result.output.lower()

    def test_ingest_start(
        self: Any, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest start' command."""
        mock_service_client.start_ingestion.return_value = {"job_id": "test-123"}
        mock_service_client.base_url = "http://localhost:8000/v1"
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "codestory.cli.commands.ingest._show_progress"
        ), patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            with patch(
                "codestory.cli.commands.ingest.setup_repository_mount",
                return_value=True,
            ), patch(
                "codestory.cli.commands.ingest.wait_for_service", return_value=True
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

    def test_ingest_start_with_priority(
        self: Any, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest start' command with --priority option."""
        mock_service_client.start_ingestion.return_value = {"job_id": "test-123"}
        mock_service_client.base_url = "http://localhost:8000/v1"
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "codestory.cli.commands.ingest._show_progress"
        ), patch("codestory.cli.main.ServiceClient", return_value=mock_service_client):
            with patch(
                "codestory.cli.commands.ingest.setup_repository_mount",
                return_value=True,
            ), patch(
                "codestory.cli.commands.ingest.wait_for_service", return_value=True
            ):
                result = cli_runner.invoke(
                    app, ["ingest", "start", temp_dir, "--priority", "high"]
                )
            assert result.exit_code == 0
            assert "Starting ingestion" in result.output
            assert "test-123" in result.output
            mock_service_client.start_ingestion.assert_called_once()
            call_args = mock_service_client.start_ingestion.call_args
            assert call_args.kwargs.get("priority") == "high"

    def test_ingest_start_no_progress(
        self: Any, cli_runner: CliRunner, mock_service_client: MagicMock
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
                "codestory.cli.commands.ingest.wait_for_service", return_value=True
            ):
                result = cli_runner.invoke(
                    app, ["ingest", "start", temp_dir, "--no-progress"]
                )
            assert result.exit_code == 0
            assert "Starting ingestion" in result.output
            assert "test-123" in result.output
            mock_show_progress.assert_not_called()

    def test_ingest_start_error(
        self: Any, cli_runner: CliRunner, mock_service_client: MagicMock
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
        self: Any,
        cli_runner: CliRunner,
        mock_service_client: MagicMock,
        sample_ingestion_status: dict,
    ) -> None:
        """Test 'ingest status' command."""
        mock_service_client.get_ingestion_status.return_value = sample_ingestion_status
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "status", "test-123"])
        assert result.exit_code == 0
        assert "Status" in result.output
        assert "test-123" in result.output
        assert "filesystem" in result.output
        assert "blarify" in result.output
        mock_service_client.get_ingestion_status.assert_called_once_with("test-123")

    def test_ingest_stop(
        self: Any, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest stop' command."""
        mock_service_client.stop_ingestion.return_value = {"success": True}
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "stop", "test-123"])
        assert result.exit_code == 0
        assert "Stopping job" in result.output
        assert "stopped" in result.output
        mock_service_client.stop_ingestion.assert_called_once_with("test-123")

    def test_ingest_stop_error(
        self: Any, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest stop' with error."""
        mock_service_client.stop_ingestion.return_value = {
            "success": False,
            "message": "Job not found",
        }
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "stop", "test-123"])
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Job not found" in result.output

    def test_ingest_jobs(
        self: Any, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest jobs' command."""
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
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "jobs"])
        assert result.exit_code == 0
        assert "Ingestion Jobs" in result.output
        assert "job-1" in result.output
        assert "job-2" in result.output
        assert "completed" in result.output.lower()
        assert "running" in result.output.lower()
        mock_service_client.list_ingestion_jobs.assert_called_once()

    def test_ingest_jobs_empty(
        self: Any, cli_runner: CliRunner, mock_service_client: MagicMock
    ) -> None:
        """Test 'ingest jobs' with no jobs."""
        mock_service_client.list_ingestion_jobs.return_value = []
        with patch(
            "codestory.cli.main.ServiceClient", return_value=mock_service_client
        ):
            result = cli_runner.invoke(app, ["ingest", "jobs"])
        assert result.exit_code == 0
        assert "No ingestion jobs found" in result.output

    def test_is_repo_mounted(self: Any) -> None:
        """Test the is_repo_mounted function."""
        with patch("subprocess.run") as mock_run:
            mock_console = MagicMock()
            service_check = MagicMock()
            service_check.stdout = "codestory-service"
            directory_check = MagicMock()
            directory_check.returncode = 1
            mock_run.side_effect = [service_check, directory_check]
            result = ingest.is_repo_mounted("/fake/repo", mock_console)
            assert not result
            mock_run.reset_mock()
            mock_run.side_effect = None
            service_check = MagicMock()
            service_check.stdout = "codestory-service"
            directory_check = MagicMock()
            directory_check.returncode = 0
            file_check = MagicMock()
            file_check.stdout = "exists"
            mock_run.side_effect = [service_check, directory_check, file_check]
            result = ingest.is_repo_mounted("/fake/repo", mock_console)
            assert result

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
                                    mock_console = MagicMock()
                                    mock_docker.return_value = True
                                    mock_mounted.return_value = False
                                    mock_create_file.return_value = True
                                    mock_run.return_value = True
                                    mock_wait.return_value = True
                                    mock_config.return_value = True
                                    result = ingest.setup_repository_mount(
                                        temp_dir, mock_console
                                    )
                                    assert result
                                    mock_docker.assert_called_once()
                                    mock_create_file.assert_called_once()
                                    mock_run.assert_called_once()
                                    mock_wait.assert_called_once()
                                    mock_config.assert_called_once()
                                    mock_docker.reset_mock()
                                    mock_mounted.reset_mock()
                                    mock_create_file.reset_mock()
                                    mock_run.reset_mock()
                                    mock_wait.reset_mock()
                                    mock_config.reset_mock()
                                    mock_docker.return_value = True
                                    mock_mounted.return_value = True
                                    result = ingest.setup_repository_mount(
                                        temp_dir, mock_console
                                    )
                                    assert result
                                    mock_mounted.assert_called_once()
                                    mock_create_file.assert_not_called()

    def test_ingest_mount_command(self: Any, cli_runner: CliRunner) -> None:
        """Test the 'ingest mount' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "codestory.cli.commands.ingest.setup_repository_mount"
            ) as mock_setup:
                mock_setup.return_value = True
                result = cli_runner.invoke(app, ["ingest", "mount", temp_dir])
                assert result.exit_code == 0
                assert "mount" in result.output.lower()
                assert "Successfully mounted" in result.output
                mock_setup.assert_called_once()
                mock_setup.reset_mock()
                mock_setup.return_value = False
                result = cli_runner.invoke(app, ["ingest", "mount", temp_dir])
                assert result.exit_code == 0
                assert "Failed to mount" in result.output
