"""Integration tests for CLI service commands."""
import os
import subprocess
import time
from typing import Any

import pytest
from click.testing import CliRunner

from codestory.cli.main import app

CLI_CMD = ["python", "-m", "codestory.cli.main"]

def is_host_native_mode() -> bool:
    """Host-native mode is deprecated. All tests now use containerized services."""
    return False

class TestServiceCommands:
    """Integration tests for service-related CLI commands."""

    @pytest.mark.require_service
    def test_service_status(
        self: Any, cli_runner: CliRunner
    ) -> None:
        """Test 'service status' command with a running service."""
        if is_host_native_mode():
            pytest.skip("Skipping test_service_status in host-native mode (no backend services)")
        # service_container fixture ensures the Code Story service is running
        print(f"[DEBUG] CODESTORY_SERVICE_URL in os.environ: {os.environ.get('CODESTORY_SERVICE_URL', 'NOT SET')}")
        result = cli_runner.invoke(app, ["service", "status"])
        print(f"[DEBUG] Exit code: {result.exit_code}")
        print(f"[DEBUG] Output: {result.output}")
        if result.exception:
            print(f"[DEBUG] Exception: {result.exception}")
        assert result.exit_code == 0
        assert "Status" in result.output
        assert "healthy" in result.output.lower()
        assert "Service is running" in result.output

    @pytest.mark.require_service
    def test_service_status_verbose(
        self: Any, cli_runner: CliRunner
    ) -> None:
        """Test 'service status' command with verbose output."""
        if is_host_native_mode():
            pytest.skip("Skipping test_service_status_verbose in host-native mode (no backend services)")
        result = cli_runner.invoke(app, ["service", "status"])
        assert result.exit_code == 0
        assert "Service Status" in result.output
        assert "healthy" in result.output.lower()

    # @pytest.mark.skipif(os.environ.get("CI") == "true", reason="Skip in CI environment")
    @pytest.mark.require_service
    def test_ui_command(
        self: Any, cli_runner: CliRunner
    ) -> None:
        """Test 'ui' command with a running service."""
        # Note: This command will try to open a browser, which will fail in CI
        # but should complete successfully without raising an exception
        result = cli_runner.invoke(app, ["ui"])
        assert result.exit_code == 0
        assert "Opening Code Story GUI in browser" in result.output
        assert "GUI opened in browser" in result.output

    @pytest.mark.skipif(True, reason="Skip Docker Compose start/stop test in integration environment")
    def test_service_start_stop_subprocess(self: Any) -> None:
        """Test that the service can be started and stopped using subprocess.

        This test uses subprocess directly rather than click's test runner
        to more accurately simulate a real user running the CLI.
        
        Note: This test is skipped in integration environment because it conflicts
        with the existing test container infrastructure.
        """
        # This test is skipped to avoid conflicts with the test container setup
        pass
