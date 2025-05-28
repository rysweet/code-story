"""
Unit tests for auto-mount functionality in the ingest command.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from codestory.cli.client.service_client import ServiceClient
from codestory.cli.commands.ingest import ingest


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
        with (
            patch(
                "codestory.cli.require_service_available.require_service_available",
                return_value=None,
            ),
            tempfile.TemporaryDirectory() as repo_path,
        ):
            cli_context["client"].base_url = "http://localhost:8000/v1"
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = "codestory-service"
                mock_run.return_value.returncode = 0
                with patch("codestory.cli.commands.ingest.os.path.exists") as mock_exists:
                    mock_exists.return_value = False
                    with patch.object(cli_context["client"], "start_ingestion") as mock_start:
                        mock_start.return_value = {"job_id": "test-job-id"}
                        # Use CLI runner to invoke the command
                        result = cli_runner.invoke(
                            ingest,
                            ["start", repo_path, "--no-progress"],
                            obj=cli_context,
                        )
                        assert result.exit_code == 0
                        args, kwargs = mock_start.call_args
                        assert kwargs == {}
                        repo_name = os.path.basename(os.path.abspath(repo_path))
                        expected_container_path = f"/repositories/{repo_name}"
                        assert args[0] == expected_container_path
                        assert len(args) == 1

    def test_auto_mount_execution(self, cli_runner, cli_context):
        """Test that auto_mount.py is executed when repository is not mounted."""
        with (
            patch(
                "codestory.cli.require_service_available.require_service_available",
                return_value=None,
            ),
            tempfile.TemporaryDirectory() as repo_path,
        ):
            cli_context["client"].base_url = "http://localhost:8000/v1"
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(stdout="codestory-service", returncode=0),
                    MagicMock(stdout="", returncode=1),
                    MagicMock(returncode=0),
                ]
                os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    ),
                    "scripts",
                    "auto_mount.py",
                )
                with patch("codestory.cli.commands.ingest.os.path.exists") as mock_exists:
                    mock_exists.return_value = True
                    with (
                        patch("sys.executable", new="python"),
                        patch(
                            "codestory.cli.commands.ingest.is_repo_mounted",
                            return_value=True,
                        ),
                        patch(
                            "codestory.cli.commands.ingest.setup_repository_mount",
                            return_value=True,
                        ),
                        patch.object(cli_context["client"], "start_ingestion") as mock_start,
                    ):
                        mock_start.return_value = {"job_id": "test-job-id"}
                        with patch("codestory.cli.commands.ingest._show_progress") as mock_progress:
                            mock_progress.return_value = None
                            result = cli_runner.invoke(
                                ingest,
                                ["start", repo_path, "--no-progress"],
                                obj=cli_context,
                            )
                            print("CLI output:", result.output)
                            print("Exit code:", result.exit_code)
                            print("Exception:", result.exception)
                            print(
                                "mock_start.call_args:",
                                getattr(mock_start, "call_args", None),
                            )
                            assert result.exit_code == 0
                            args, kwargs = mock_start.call_args
                            assert kwargs == {}
                            repo_name = os.path.basename(os.path.abspath(repo_path))
                            expected_container_path = f"/repositories/{repo_name}"
                            assert args[0] == expected_container_path
                            assert len(args) == 1

    def test_no_auto_mount(self, cli_runner, cli_context):
        """Test that --no-auto-mount flag disables auto mounting."""
        with (
            patch(
                "codestory.cli.require_service_available.require_service_available",
                return_value=None,
            ),
            tempfile.TemporaryDirectory() as repo_path,
        ):
            cli_context["client"].base_url = "http://localhost:8000/v1"
            with (
                patch("subprocess.run") as mock_run,
                patch.object(cli_context["client"], "start_ingestion") as mock_start,
            ):
                mock_start.return_value = {"job_id": "test-job-id"}
                result = cli_runner.invoke(
                    ingest,
                    ["start", repo_path, "--no-progress", "--no-auto-mount"],
                    obj=cli_context,
                )
                assert result.exit_code == 0
                assert mock_run.call_count == 0
                args, kwargs = mock_start.call_args
                assert kwargs == {}
                repo_name = os.path.basename(os.path.abspath(repo_path))
                expected_container_path = f"/repositories/{repo_name}"
                assert args[0] == expected_container_path
                assert len(args) == 1

    def test_non_docker_deployment(self, cli_runner, cli_context):
        """Test behavior with non-Docker deployment."""
        with (
            patch(
                "codestory.cli.require_service_available.require_service_available",
                return_value=None,
            ),
            tempfile.TemporaryDirectory() as repo_path,
        ):
            cli_context["client"].base_url = "https://remote-server.com/v1"
            with (
                patch("subprocess.run") as mock_run,
                patch.object(cli_context["client"], "start_ingestion") as mock_start,
            ):
                mock_start.return_value = {"job_id": "test-job-id"}
                result = cli_runner.invoke(
                    ingest,
                    ["start", repo_path, "--no-progress"],
                    obj=cli_context,
                )
                assert result.exit_code == 0
                assert mock_run.call_count == 0
                args, kwargs = mock_start.call_args
                assert kwargs == {}
                # For remote base_url, the local path is used
                assert args[0] == os.path.abspath(repo_path)
                assert len(args) == 1


class TestAutoMountFlags:
    """Tests for auto-mount related CLI flags."""

    def test_auto_mount_flag(self, cli_runner, cli_context):
        """Test that --auto-mount flag works as expected."""
        with (
            patch(
                "codestory.cli.require_service_available.require_service_available",
                return_value=None,
            ),
            tempfile.TemporaryDirectory() as repo_path,
        ):
            cli_context["client"].base_url = "http://localhost:8000/v1"
            with (
                patch("subprocess.run"),
                patch.object(cli_context["client"], "start_ingestion") as mock_start,
            ):
                mock_start.return_value = {"job_id": "test-job-id"}
                with patch("codestory.cli.commands.ingest._show_progress") as mock_progress:
                    mock_progress.return_value = None
                    result = cli_runner.invoke(
                        ingest,
                        ["start", repo_path, "--auto-mount", "--no-progress"],
                        obj=cli_context,
                    )
                    print("CLI output:", result.output)
                    print("Exit code:", result.exit_code)
                    print("Exception:", result.exception)
                    print(
                        "mock_start.call_args:",
                        getattr(mock_start, "call_args", None),
                    )
                    assert result.exit_code == 0
                    call_args = mock_start.call_args
                    assert call_args is not None
                    args, kwargs = call_args
                    repo_name = os.path.basename(os.path.abspath(repo_path))
                    expected_container_path = f"/repositories/{repo_name}"
                    assert args[0] == expected_container_path
                    assert len(args) == 1

    def test_no_auto_mount_flag(self, cli_runner, cli_context):
        """Test that --no-auto-mount flag works as expected."""
        with (
            patch(
                "codestory.cli.require_service_available.require_service_available",
                return_value=None,
            ),
            tempfile.TemporaryDirectory() as repo_path,
        ):
            cli_context["client"].base_url = "http://localhost:8000/v1"
            with (
                patch("subprocess.run"),
                patch.object(cli_context["client"], "start_ingestion") as mock_start,
            ):
                mock_start.return_value = {"job_id": "test-job-id"}
                with patch("codestory.cli.commands.ingest._show_progress") as mock_progress:
                    mock_progress.return_value = None
                    result = cli_runner.invoke(
                        ingest,
                        [
                            "start",
                            repo_path,
                            "--no-auto-mount",
                            "--no-progress",
                        ],
                        obj=cli_context,
                    )
                    print("CLI output:", result.output)
                    print("Exit code:", result.exit_code)
                    print("Exception:", result.exception)
                    print(
                        "mock_start.call_args:",
                        getattr(mock_start, "call_args", None),
                    )
                    assert result.exit_code == 0
                    call_args = mock_start.call_args
                    assert call_args is not None
                    args, kwargs = call_args
                    repo_name = os.path.basename(os.path.abspath(repo_path))
                    expected_container_path = f"/repositories/{repo_name}"
                    assert args[0] == expected_container_path
                    assert len(args) == 1
