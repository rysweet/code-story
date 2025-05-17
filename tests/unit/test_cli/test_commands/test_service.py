"""Tests for the service command group in the CLI."""

import pytest
from unittest import mock
from click.testing import CliRunner

from rich.console import Console

from codestory.cli.commands.service import service, renew_azure_auth
from codestory.cli.client.service_client import ServiceClient, ServiceError


class TestServiceCommand:
    """Tests for the service command group."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock ServiceClient."""
        client = mock.MagicMock(spec=ServiceClient)
        # Mock check_service_health
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
    def cli_runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def ctx_obj(self, mock_client):
        """Create a Click context object."""
        console = Console(width=100, color_system=None)
        return {"client": mock_client, "console": console}

    def test_auth_renew_command_exists(self):
        """Test that auth-renew command exists."""
        # Get all commands in the service group
        commands = service.commands
        
        # Check if auth-renew is in the commands
        assert "auth-renew" in commands

    def test_auth_renew_help(self, cli_runner):
        """Test that auth-renew command has correct help text."""
        # Run the command with --help flag
        result = cli_runner.invoke(service, ["auth-renew", "--help"])
        
        # Check output contains expected help text
        assert result.exit_code == 0
        assert "Renew Azure authentication tokens" in result.output
        assert "--tenant" in result.output
        assert "--check" in result.output
        assert "--verbose" in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_inside_container(
        self, mock_exists, mock_get_containers, mock_run, cli_runner, ctx_obj
    ):
        """Test auth-renew command when run inside a container."""
        # Mock being inside a container
        mock_exists.return_value = True  # /.dockerenv exists
        mock_run.return_value = mock.MagicMock(returncode=0)
        
        # Run the command
        result = cli_runner.invoke(
            renew_azure_auth,
            [],
            obj=ctx_obj,
            catch_exceptions=False,
        )
        
        # Check that correct methods were called
        assert result.exit_code == 0
        mock_run.assert_called_once()
        
        # Assert subprocess.run was called with the right command
        args, kwargs = mock_run.call_args
        assert "azure_auth_renew.py" in str(args[0])
        
        # Check output
        assert "Azure authentication renewed successfully" in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_specific_tenant(
        self, mock_exists, mock_get_containers, mock_run, cli_runner, ctx_obj
    ):
        """Test auth-renew command with specific tenant ID."""
        # Mock being inside a container
        mock_exists.return_value = True  # /.dockerenv exists
        mock_run.return_value = mock.MagicMock(returncode=0)
        
        # Run the command
        result = cli_runner.invoke(
            renew_azure_auth,
            ["--tenant", "12345678-1234-1234-1234-123456789012"],
            obj=ctx_obj,
            catch_exceptions=False,
        )
        
        # Check that correct methods were called
        assert result.exit_code == 0
        mock_run.assert_called_once()
        
        # Assert subprocess.run was called with the right command and tenant
        args, kwargs = mock_run.call_args
        assert "azure_auth_renew.py" in str(args[0])
        assert "--tenant" in str(args[0])
        assert "12345678-1234-1234-1234-123456789012" in str(args[0])
        
        # Check output
        assert "Azure authentication renewed successfully" in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_check_only(
        self, mock_exists, mock_get_containers, mock_run, cli_runner, ctx_obj
    ):
        """Test auth-renew command with check-only flag."""
        # Mock being inside a container
        mock_exists.return_value = True  # /.dockerenv exists
        mock_run.return_value = mock.MagicMock(returncode=0)
        
        # Run the command
        result = cli_runner.invoke(
            renew_azure_auth,
            ["--check"],
            obj=ctx_obj,
            catch_exceptions=False,
        )
        
        # Check that correct methods were called
        assert result.exit_code == 0
        mock_run.assert_called_once()
        
        # Assert subprocess.run was called with the right command and check flag
        args, kwargs = mock_run.call_args
        assert "azure_auth_renew.py" in str(args[0])
        assert "--check" in str(args[0])
        
        # Check output
        assert "Azure authentication renewed successfully" in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_error_handling(
        self, mock_exists, mock_get_containers, mock_run, cli_runner, ctx_obj
    ):
        """Test auth-renew error handling."""
        # Mock being inside a container
        mock_exists.return_value = True  # /.dockerenv exists
        mock_run.return_value = mock.MagicMock(returncode=1)
        
        # Run the command
        result = cli_runner.invoke(
            renew_azure_auth,
            [],
            obj=ctx_obj,
            catch_exceptions=False,
        )
        
        # Check that correct methods were called
        assert result.exit_code == 1
        mock_run.assert_called_once()
        
        # Check output
        assert "Auth renewal failed" in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_outside_container(
        self, mock_exists, mock_get_containers, mock_run, cli_runner, ctx_obj
    ):
        """Test auth-renew command when run on host (outside container)."""
        # Mock being outside a container
        mock_exists.return_value = False  # /.dockerenv doesn't exist
        
        # Mock running containers
        mock_get_containers.return_value = ["codestory-service", "codestory-worker"]
        
        # Mock subprocess run 
        mock_run.return_value = mock.MagicMock(returncode=0)
        
        # Run the command
        result = cli_runner.invoke(
            renew_azure_auth,
            [],
            obj=ctx_obj,
            catch_exceptions=False,
        )
        
        # Check that correct methods were called
        assert result.exit_code == 0
        mock_get_containers.assert_called_once()
        mock_run.assert_called_once()
        
        # Assert subprocess.run was called with a docker exec command
        args, kwargs = mock_run.call_args
        assert "docker" in str(args[0])
        assert "exec" in str(args[0])
        assert "codestory-service" in str(args[0])
        assert "azure_auth_renew.py" in str(args[0])
        
        # Check output
        assert "Azure authentication renewed successfully" in result.output

    @mock.patch("codestory.cli.commands.service.subprocess.run")
    @mock.patch("codestory.cli.commands.service.get_running_containers")
    @mock.patch("codestory.cli.commands.service.os.path.exists")
    def test_auth_renew_no_containers(
        self, mock_exists, mock_get_containers, mock_run, cli_runner, ctx_obj
    ):
        """Test auth-renew when no containers are running."""
        # Mock being outside a container
        mock_exists.return_value = False  # /.dockerenv doesn't exist
        
        # Mock no running containers
        mock_get_containers.return_value = []
        
        # Run the command
        result = cli_runner.invoke(
            renew_azure_auth,
            [],
            obj=ctx_obj,
            catch_exceptions=False,
        )
        
        # Check output and exit code
        assert result.exit_code == 1
        assert "No Code Story containers found running" in result.output