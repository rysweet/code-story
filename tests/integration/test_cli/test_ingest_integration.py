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
    def test_ingest_start_and_status(self: Any, cli_runner: CliRunner, running_service: dict[str, Any], test_repository: str) -> None:
        """Test 'ingest start' and 'ingest status' commands with real repository."""
        result = cli_runner.invoke(app, ['ingest', 'start', test_repository, '--no-progress'])
        assert result.exit_code == 0
        assert 'Starting ingestion' in result.output
        job_id_line = next((line for line in result.output.splitlines() if 'Job ID:' in line))
        job_id = job_id_line.split('Job ID:')[1].strip()
        assert job_id
        time.sleep(1)
        status_result = cli_runner.invoke(app, ['ingest', 'status', job_id])
        assert status_result.exit_code == 0
        assert job_id in status_result.output
        assert 'filesystem' in status_result.output.lower() or 'running' in status_result.output.lower()

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_ingest_start_with_countdown(self: Any, cli_runner: CliRunner, running_service: dict[str, Any], test_repository: str) -> None:
        """Test 'ingest start' with --countdown schedules job for delayed execution."""
        result = cli_runner.invoke(app, ['ingest', 'start', test_repository, '--no-progress', '--countdown', '5'])
        assert result.exit_code == 0
        assert 'Starting ingestion' in result.output
        job_id_line = next((line for line in result.output.splitlines() if 'Job ID:' in line))
        job_id = job_id_line.split('Job ID:')[1].strip()
        assert job_id
        status_result = cli_runner.invoke(app, ['ingest', 'status', job_id])
        assert status_result.exit_code == 0
        assert job_id in status_result.output
        assert 'pending' in status_result.output.lower() or 'waiting' in status_result.output.lower() or 'scheduled' in status_result.output.lower()
        time.sleep(7)

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_ingest_start_with_eta(self: Any, cli_runner: CliRunner, running_service: dict[str, Any], test_repository: str) -> None:
        """Test 'ingest start' with --eta schedules job for delayed execution at a specific time."""
        from datetime import datetime, timedelta
        eta_time = datetime.now() + timedelta(seconds=10)
        eta_iso = eta_time.isoformat()
        result = cli_runner.invoke(app, ['ingest', 'start', test_repository, '--no-progress', '--eta', eta_iso])
        assert result.exit_code == 0
        assert 'Starting ingestion' in result.output
        job_id_line = next((line for line in result.output.splitlines() if 'Job ID:' in line))
        job_id = job_id_line.split('Job ID:')[1].strip()
        assert job_id
        status_result = cli_runner.invoke(app, ['ingest', 'status', job_id])
        assert status_result.exit_code == 0
        assert job_id in status_result.output
        assert 'pending' in status_result.output.lower() or 'waiting' in status_result.output.lower() or 'scheduled' in status_result.output.lower()
        assert 'eta' in status_result.output.lower() or 'scheduled' in status_result.output.lower()
        time.sleep(12)
        status_result2 = cli_runner.invoke(app, ['ingest', 'status', job_id])
        assert status_result2.exit_code == 0
        assert job_id in status_result2.output
        assert 'running' in status_result2.output.lower() or 'completed' in status_result2.output.lower() or 'filesystem' in status_result2.output.lower()
        status_result2 = cli_runner.invoke(app, ['ingest', 'status', job_id])
        assert status_result2.exit_code == 0
        assert job_id in status_result2.output
        assert 'running' in status_result2.output.lower() or 'completed' in status_result2.output.lower() or 'filesystem' in status_result2.output.lower()

    @pytest.mark.integration
    def test_ingest_start_command_format(self: Any, cli_runner: CliRunner) -> None:
        """Test that 'ingest start' uses positional arguments correctly."""
        invalid_result = cli_runner.invoke(app, ['ingest', 'start', '--path', '.'])
        assert invalid_result.exit_code != 0
        assert 'Error: No such option: --path' in invalid_result.output
        help_result = cli_runner.invoke(app, ['ingest', 'start', '--help'])
        assert help_result.exit_code == 0
        assert 'Usage: app ingest start [OPTIONS] REPOSITORY_PATH' in help_result.output
        assert 'REPOSITORY_PATH' in help_result.output

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_ingest_jobs_list(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'ingest jobs' command with real service."""
        result = cli_runner.invoke(app, ['ingest', 'jobs'])
        assert result.exit_code == 0
        assert 'Ingestion Jobs' in result.output or 'No ingestion jobs found' in result.output

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_mount_command(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test the 'ingest mount' command with a real repository."""
        if not is_docker_running():
            pytest.skip('Docker is not running, skipping test')
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, 'test.txt'), 'w') as f:
                f.write('test content')
            result = cli_runner.invoke(app, ['ingest', 'mount', temp_dir, '--debug'], catch_exceptions=False)
            assert result.exit_code == 0
            assert 'Successfully mounted' in result.output or 'already mounted' in result.output
            assert is_repo_mounted(temp_dir)

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_force_remount(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test the '--force-remount' option with a real repository."""
        if not is_docker_running():
            pytest.skip('Docker is not running, skipping test')
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, 'test.txt'), 'w') as f:
                f.write('test content')
            cli_runner.invoke(app, ['ingest', 'mount', temp_dir])
            result = cli_runner.invoke(app, ['ingest', 'mount', temp_dir, '--force-remount'], catch_exceptions=False)
            assert result.exit_code == 0
            assert 'Successfully mounted' in result.output
            assert is_repo_mounted(temp_dir)