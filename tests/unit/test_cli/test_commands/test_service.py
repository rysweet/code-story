from typing import Any

"Tests for the service command group in the CLI."
import sys
from unittest import mock

import pytest
from click.testing import CliRunner
from rich.console import Console

from codestory.cli.client.service_client import ServiceClient
from codestory.cli.commands.service import renew_azure_auth, service


class TestServiceCommand:
    """Tests for the service command group."""

    @pytest.fixture
    def mock_client(self: Any) -> Any:
        """Create a mock ServiceClient."""
        client = mock.MagicMock(spec=ServiceClient)
        client.check_service_health.return_value = {
            "status": "healthy",
            "components": {
                "neo4j": {"status": "healthy"},
                "redis": {"status": "healthy"},
                "celery": {"status": "healthy"},
                "openai": {"status": "healthy"},
            },
        }
        return client

    @pytest.fixture
    def cli_runner(self: Any) -> Any:
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def ctx_obj(self: Any, mock_client: Any) -> Any:
        """Create a Click context object."""
        console = Console(width=100, color_system=None)
        return {"client": mock_client, "console": console}

    def test_auth_renew_command_exists(self: Any) -> None:
        """Test that auth-renew command exists."""
        commands = service.commands
        assert "auth-renew" in commands

    def test_auth_renew_help(self: Any, cli_runner: Any) -> None:
        """Test that auth-renew command has correct help text."""
        result = cli_runner.invoke(service, ["auth-renew", "--help"])
        assert result.exit_code == 0
        assert "Renew Azure authentication tokens" in result.output
        assert "--tenant" in result.output
        assert "--check" in result.output
        assert "--verbose" in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_inside_container(
        self: Any,
        mock_exists: Any,
        mock_get_containers: Any,
        mock_run: Any,
        cli_runner: Any,
        ctx_obj: Any,
    ) -> None:
        """Test auth-renew command when run inside a container."""
        mock_exists.return_value = True
        mock_run.return_value = mock.MagicMock(returncode=0)
        result = cli_runner.invoke(
            renew_azure_auth, [], obj=ctx_obj, catch_exceptions=False
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert "inject_azure_tokens.py" in str(args[0])
        assert "Azure authentication tokens updated successfully." in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_specific_tenant(
        self: Any,
        mock_exists: Any,
        mock_get_containers: Any,
        mock_run: Any,
        cli_runner: Any,
        ctx_obj: Any,
    ) -> None:
        """Test auth-renew command with specific tenant ID."""
        mock_exists.return_value = True
        mock_run.return_value = mock.MagicMock(returncode=0)
        result = cli_runner.invoke(
            renew_azure_auth,
            ["--tenant", "12345678-1234-1234-1234-123456789012"],
            obj=ctx_obj,
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert "inject_azure_tokens.py" in str(args[0])
        assert "--tenant" in str(args[0])
        assert "12345678-1234-1234-1234-123456789012" in str(args[0])
        assert "Azure authentication tokens updated successfully." in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_check_only(
        self: Any,
        mock_exists: Any,
        mock_get_containers: Any,
        mock_run: Any,
        cli_runner: Any,
        ctx_obj: Any,
    ) -> None:
        """Test auth-renew command with check-only flag."""
        mock_exists.return_value = True
        mock_run.return_value = mock.MagicMock(returncode=0)
        result = cli_runner.invoke(
            renew_azure_auth, ["--check"], obj=ctx_obj, catch_exceptions=False
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert "inject_azure_tokens.py" in str(args[0])
        assert "Azure authentication tokens updated successfully." in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_error_handling(
        self: Any,
        mock_exists: Any,
        mock_get_containers: Any,
        mock_run: Any,
        cli_runner: Any,
        ctx_obj: Any,
    ) -> None:
        """Test auth-renew error handling."""
        mock_exists.return_value = True
        mock_run.return_value = mock.MagicMock(returncode=1)
        result = cli_runner.invoke(
            renew_azure_auth, [], obj=ctx_obj, catch_exceptions=False
        )
        assert result.exit_code == 1
        mock_run.assert_called_once()
        assert "Azure authentication renewal failed." in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_outside_container(
        self: Any,
        mock_exists: Any,
        mock_get_containers: Any,
        mock_run: Any,
        cli_runner: Any,
        ctx_obj: Any,
    ) -> None:
        """Test auth-renew command when run on host (outside container)."""
        mock_exists.return_value = False
        mock_get_containers.return_value = ["codestory-service", "codestory-worker"]
        mock_run.return_value = mock.MagicMock(returncode=0)
        result = cli_runner.invoke(
            renew_azure_auth, [], obj=ctx_obj, catch_exceptions=False
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert sys.executable in args[0][0]
        assert "inject_azure_tokens.py" in str(args[0])
        assert "Azure authentication renewed successfully." in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_no_containers(
        self: Any,
        mock_exists: Any,
        mock_get_containers: Any,
        mock_run: Any,
        cli_runner: Any,
        ctx_obj: Any,
    ) -> None:
        """Test auth-renew when no containers are running."""
        mock_exists.return_value = False
        mock_get_containers.return_value = []
        result = cli_runner.invoke(
            renew_azure_auth, [], obj=ctx_obj, catch_exceptions=False
        )
        assert result.exit_code == 1
        assert "Token injection failed." in result.output
