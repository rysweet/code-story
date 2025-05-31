"""Integration tests for CLI service commands."""
import os
import subprocess
import time
from typing import Any
import pytest
from click.testing import CliRunner
from codestory.cli.main import app
CLI_CMD = ['python', '-m', 'codestory.cli.main']

class TestServiceCommands:
    """Integration tests for service-related CLI commands."""

    @pytest.mark.require_service
    def test_service_status(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'service status' command with a running service."""
        result = cli_runner.invoke(app, ['service', 'status'])
        assert result.exit_code == 0
        assert 'Status' in result.output
        assert 'healthy' in result.output.lower()
        assert 'Service is running' in result.output

    @pytest.mark.require_service
    def test_service_info(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'service info' command with a running service."""
        result = cli_runner.invoke(app, ['service', 'info'])
        assert result.exit_code == 0
        assert 'Code Story Service Information' in result.output
        assert str(running_service['port']) in result.output

    @pytest.mark.skipif(os.environ.get('CI') == 'true', reason='Skip in CI environment')
    @pytest.mark.require_service
    def test_service_ui_open(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'ui open' command with a running service."""
        with pytest.raises(SystemExit) as exc_info:
            cli_runner.invoke(app, ['ui', 'open'], catch_exceptions=False)
        assert exc_info.value.code in [0, None]

    @pytest.mark.skipif(os.environ.get('CI') == 'true', reason='Skip in CI environment')
    def test_service_start_stop_subprocess(self: Any) -> None:
        """Test that the service can be started and stopped using subprocess.

        This test uses subprocess directly rather than click's test runner
        to more accurately simulate a real user running the CLI.
        """
        try:
            subprocess.run([*CLI_CMD, 'service', 'stop'], check=False, capture_output=True, text=True, timeout=30)
            time.sleep(2)
        except Exception:
            pass
        start_result = subprocess.run([*CLI_CMD, 'service', 'start', '--detach'], check=False, capture_output=True, text=True, timeout=60)
        assert 'Starting Code Story service' in start_result.stdout
        time.sleep(5)
        status_result = subprocess.run([*CLI_CMD, 'service', 'status'], check=False, capture_output=True, text=True, timeout=30)
        assert 'Checking Code Story service status' in status_result.stdout
        stop_result = subprocess.run([*CLI_CMD, 'service', 'stop'], check=False, capture_output=True, text=True, timeout=30)
        assert 'Stopping Code Story service' in stop_result.stdout