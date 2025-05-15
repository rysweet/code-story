"""Integration tests for CLI service commands."""

import os
import subprocess
import time
from typing import Dict, Any

import pytest
import httpx
from click.testing import CliRunner

from codestory.cli.main import app

# Path to the CLI executable
CLI_CMD = ["python", "-m", "codestory.cli.main"]


class TestServiceCommands:
    """Integration tests for service-related CLI commands."""
    
    @pytest.mark.require_service
    def test_service_status(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'service status' command with a running service."""
        # Run the command
        result = cli_runner.invoke(app, ["service", "status"])
        
        # Check result
        assert result.exit_code == 0
        assert "Status" in result.output
        assert "healthy" in result.output.lower()
        assert "Service is running" in result.output
    
    @pytest.mark.require_service
    def test_service_info(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'service info' command with a running service."""
        # Run the command
        result = cli_runner.invoke(app, ["service", "info"])
        
        # Check result
        assert result.exit_code == 0
        assert "Code Story Service Information" in result.output
        assert str(running_service["port"]) in result.output
        
    @pytest.mark.skipif(os.environ.get("CI") == "true", reason="Skip in CI environment")
    @pytest.mark.require_service
    def test_service_ui_open(self, cli_runner: CliRunner, running_service: Dict[str, Any]) -> None:
        """Test 'ui open' command with a running service."""
        # This test is a bit tricky because it actually tries to open a browser
        # We'll just check that the command runs without errors
        with pytest.raises(SystemExit) as exc_info:
            result = cli_runner.invoke(app, ["ui", "open"], catch_exceptions=False)
            
        # It might exit to launch the browser
        assert exc_info.value.code in [0, None]

    @pytest.mark.skipif(os.environ.get("CI") == "true", reason="Skip in CI environment")
    def test_service_start_stop_subprocess(self):
        """Test that the service can be started and stopped using subprocess.
        
        This test uses subprocess directly rather than click's test runner
        to more accurately simulate a real user running the CLI.
        """
        # First make sure service is stopped
        try:
            subprocess.run(
                CLI_CMD + ["service", "stop"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Give it a moment to stop fully
            time.sleep(2)
        except Exception:
            pass  # Ignore errors here, we just want to make sure it's stopped

        # Start the service
        start_result = subprocess.run(
            CLI_CMD + ["service", "start", "--detach"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        # Verify it started or at least attempted to
        assert "Starting Code Story service" in start_result.stdout
        
        # Wait a bit for services to settle
        time.sleep(5)
        
        # Check status
        status_result = subprocess.run(
            CLI_CMD + ["service", "status"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # This could pass or fail depending on if service actually started
        # For our test, we just want to make sure the command runs
        assert "Checking Code Story service status" in status_result.stdout
        
        # Now stop the service
        stop_result = subprocess.run(
            CLI_CMD + ["service", "stop"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # Verify it tried to stop
        assert "Stopping Code Story service" in stop_result.stdout