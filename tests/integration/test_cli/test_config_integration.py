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
    def test_config_show(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'config show' command with real configuration."""
        result = cli_runner.invoke(app, ['config', 'show'])
        assert result.exit_code == 0
        assert 'Configuration' in result.output
        assert 'service' in result.output.lower()
        assert 'neo4j' in result.output.lower()
        assert '***' in result.output

    @pytest.mark.integration
    @pytest.mark.require_service
    def test_config_show_sensitive(self: Any, cli_runner: CliRunner, running_service: dict[str, Any]) -> None:
        """Test 'config show --sensitive' command with real configuration."""
        result = cli_runner.invoke(app, ['config', 'show', '--sensitive'])
        assert result.exit_code == 0
        assert 'Configuration' in result.output
        settings = get_settings()
        if settings.neo4j.password:
            assert settings.neo4j.password.get_secret_value() in result.output