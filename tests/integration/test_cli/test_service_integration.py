"""Integration tests for CLI service commands."""

import os
import time
from typing import Dict, Any

import pytest
import httpx
from click.testing import CliRunner

from codestory.cli.main import app


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