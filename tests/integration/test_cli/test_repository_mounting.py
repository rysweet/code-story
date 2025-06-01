from typing import Any

"\nIntegration tests for repository mounting functionality.\n\nThese tests verify that the repository mounting works correctly\nwith real Docker containers and filesystem access.\n\nNote: These tests require Docker to be running and will interact\nwith real containers. They may modify your Docker environment.\n"
import os
import subprocess
import tempfile
import time

import pytest
from click.testing import CliRunner
from rich.console import Console

from codestory.cli.commands.ingest import ingest, start_ingestion

pytestmark = [
    pytest.mark.skipif(
        subprocess.run(["docker", "ps"], capture_output=True).returncode != 0,
        reason="Docker is not running",
    ),
    pytest.mark.integration,
    pytest.mark.docker,
]


@pytest.fixture
def temp_repository() -> None:
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        readme_path = os.path.join(temp_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write(
                "# Test Repository\n\nThis is a test repository for mounting tests."
            )
        py_file_path = os.path.join(temp_dir, "test_file.py")
        with open(py_file_path, "w") as f:
            f.write(
                '\ndef hello():\n    print("Hello, world!")\n\nif __name__ == "__main__":\n    hello()\n'
            )
        mount_test_path = os.path.join(temp_dir, ".mount_test")
        with open(mount_test_path, "w") as f:
            f.write(f"Mount test marker created at {time.time()}")
        yield temp_dir


@pytest.fixture
def stop_containers() -> None:
    """Stop Code Story containers before and after tests."""
    subprocess.run(["docker-compose", "down"], cwd=os.getcwd(), capture_output=True)
    yield
    subprocess.run(["docker-compose", "down"], cwd=os.getcwd(), capture_output=True)


@pytest.fixture
def cli_runner() -> Any:
    """Create a Click CLI runner for testing."""
    return CliRunner()


class TestRepositoryMounting:
    """Integration tests for repository mounting."""

    def test_mount_verification(self: Any, temp_repository: Any) -> None:
        """Test that the mount verification correctly detects issues."""
        docker_check = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if docker_check.returncode != 0:
            pytest.skip("Docker is not running")
        print(f"\nTesting repository mounting verification with: {temp_repository}")
        container_name = "codestory-mount-test"
        os.path.basename(temp_repository)
        container_path = "/test-mount"
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        start_result = subprocess.run(
            ["docker", "run", "-d", "--name", container_name, "alpine", "sleep", "60"],
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"Container start result: {start_result.stdout}")
        container_check = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
        )
        assert container_name in container_check.stdout, "Test container is not running"
        print("Test 1: Verifying path doesn't exist without mounting")
        path_check = subprocess.run(
            f"docker exec {container_name} sh -c 'test -d {container_path} && echo exists'",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        assert (
            "exists" not in path_check.stdout
        ), "Repository path should not be accessible without mounting"
        print("Test 1 passed: Path not accessible without mounting")
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        print("Test 2: Starting container with repository mounted")
        mount_result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-v",
                f"{temp_repository}:{container_path}",
                "alpine",
                "sleep",
                "60",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"Mount container start result: {mount_result.stdout}")
        container_check = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
        )
        assert (
            container_name in container_check.stdout
        ), "Test container with mount is not running"
        print("Verifying path exists with mounting")
        path_check = subprocess.run(
            f"docker exec {container_name} sh -c 'test -d {container_path} && echo exists'",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        assert (
            "exists" in path_check.stdout
        ), f"Repository path not accessible in container even with mounting: {container_path}"
        print("Test 2 passed: Path accessible with mounting")
        ls_result = subprocess.run(
            ["docker", "exec", container_name, "ls", "-la", container_path],
            capture_output=True,
            text=True,
        )
        print(f"Directory contents in container: {ls_result.stdout}")
        assert (
            "README.md" in ls_result.stdout
        ), f"Repository not mounted correctly: {ls_result.stdout}"
        assert (
            "test_file.py" in ls_result.stdout
        ), f"Repository not mounted correctly: {ls_result.stdout}"
        assert (
            ".mount_test" in ls_result.stdout
        ), f"Repository not mounted correctly: {ls_result.stdout}"
        cat_result = subprocess.run(
            ["docker", "exec", container_name, "cat", f"{container_path}/.mount_test"],
            capture_output=True,
            text=True,
        )
        assert (
            "Mount test marker created at" in cat_result.stdout
        ), f"Could not read mount test file: {cat_result.stdout}"
        inspect_result = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{json .Mounts}}"],
            capture_output=True,
            text=True,
        )
        assert (
            temp_repository in inspect_result.stdout
        ), f"Repository not found in Docker mount configuration: {inspect_result.stdout}"
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


@pytest.mark.integration
@pytest.mark.docker
class TestCliAutoMount:
    """CLI integration tests for auto mounting with ingest command."""

    def test_cli_mount_verification_function(self: Any, temp_repository: Any) -> None:
        """Test that ingest command correctly verifies container paths."""
        docker_check = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if docker_check.returncode != 0:
            pytest.skip("Docker is not running")
        from io import StringIO
        from unittest.mock import MagicMock

        print(f"\nTesting CLI mount verification with repository: {temp_repository}")
        console = Console(file=StringIO())
        mock_client = MagicMock()
        mock_client.base_url = "http://localhost:8000/v1"
        mock_client.start_ingestion.return_value = {"job_id": "test-job-id"}
        cli_context = {
            "client": mock_client,
            "console": console,
            "settings": MagicMock(),
        }
        container_name = "codestory-service"
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        subprocess.run(
            ["docker", "run", "-d", "--name", container_name, "alpine", "sleep", "60"],
            capture_output=True,
        )
        container_check = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
        )
        assert container_name in container_check.stdout, "Test container is not running"
        repo_name = os.path.basename(temp_repository)
        container_path = f"/repositories/{repo_name}"
        try:
            with pytest.raises(Exception) as excinfo:
                from click import Context

                click_ctx = Context(ingest)
                click_ctx.obj = cli_context
                start_ingestion(
                    click_ctx,
                    temp_repository,
                    no_progress=True,
                    container=True,
                    path_prefix="/repositories",
                    auto_mount=False,
                    no_auto_mount=True,
                )
            print(f"Got expected exception: {excinfo.value!s}")
            output = console.file.getvalue()
            assert "Repository not mounted" in output or "does not exist" in str(
                excinfo.value
            ), f"CLI did not detect missing mount. Output: {output}, Exception: {excinfo.value}"
            print("Test 1 passed: CLI correctly detected unmounted repository")
        finally:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-v",
                f"{temp_repository}:{container_path}",
                "alpine",
                "sleep",
                "60",
            ],
            capture_output=True,
        )
        try:
            console = Console(file=StringIO())
            cli_context["console"] = console
            from click import Context

            click_ctx = Context(ingest)
            click_ctx.obj = cli_context
            start_ingestion(
                click_ctx,
                temp_repository,
                no_progress=True,
                container=True,
                path_prefix="/repositories",
                auto_mount=False,
                no_auto_mount=True,
            )
            mock_client.start_ingestion.assert_called_once()
            call_args = mock_client.start_ingestion.call_args[0][0]
            assert (
                container_path in call_args
            ), f"Container path not passed to service: {call_args}"
            print("Test 2 passed: CLI correctly used mounted repository")
        finally:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
