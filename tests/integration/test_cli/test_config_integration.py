"""Integration tests for CLI configuration commands."""
from typing import Any

import pytest
from codestory.config import get_settings


class TestConfigCommands:
    """Integration tests for configuration-related CLI commands."""

    @pytest.mark.integration
    def test_config_show(
        self: Any, cli_runner
    ) -> None:
        """Test 'config show' command with real configuration."""
        result = cli_runner(["config", "show"])
        assert result.returncode == 0
        assert "Configuration" in result.stdout
        assert "service" in result.stdout.lower()
        assert "neo4j" in result.stdout.lower()
        assert "***" in result.stdout

    @pytest.mark.integration
    def test_config_show_sensitive(
        self: Any, cli_runner
    ) -> None:
        """Test 'config show --sensitive' command with real configuration."""
        result = cli_runner(["config", "show", "--sensitive"])
        assert result.returncode == 0
        assert "Configuration" in result.stdout
        settings = get_settings()
        if settings.neo4j.password:
            assert settings.neo4j.password.get_secret_value() in result.stdout
