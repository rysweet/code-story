"""Integration tests for CLI configuration commands."""

from typing import Any

import pytest
from click.testing import CliRunner

from codestory.cli.main import app
from codestory.config import get_settings


class TestConfigCommands:
    """Integration tests for configuration-related CLI commands."""

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_config_show(self, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'config show' command with real configuration."""
        # Show configuration
        result = cli_runner.invoke(app, ["config", "show"])

        # Check result
        assert result.exit_code == 0
        assert "Configuration" in result.output

        # Check that key sections are present
        assert "service" in result.output.lower()
        assert "neo4j" in result.output.lower()

        # Sensitive values should be masked
        assert "***" in result.output

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_config_show_sensitive(
        self, cli_runner: CliRunner, running_service: dict[str, Any]
    ) -> None:
        """Test 'config show --sensitive' command with real configuration."""
        # Show configuration including sensitive values
        result = cli_runner.invoke(app, ["config", "show", "--sensitive"])

        # Check result
        assert result.exit_code == 0
        assert "Configuration" in result.output

        # Sensitive values should be visible (though they might be empty in test)
        settings = get_settings()
        if settings.neo4j.password:
            assert settings.neo4j.password.get_secret_value() in result.output
