from typing import Any
"""
Integration tests for repository mounting functionality.

These tests verify that the repository mounting works correctly
with real Docker containers and filesystem access.

Note: These tests require Docker to be running and will interact
with real containers. They may modify your Docker environment.
"""

import os
import subprocess
import tempfile
import time

import pytest
from click.testing import CliRunner
from rich.console import Console

from codestory.cli.commands.ingest import ingest, start_ingestion

# Mark these tests as requiring Docker
pytestmark = [
    pytest.mark.skipif(
        subprocess.run(["docker", "ps"], capture_output=True).returncode != 0,
        reason="Docker is not running",
    ),
    pytest.mark.integration,  # Mark as integration tests
    pytest.mark.docker,  # Mark as requiring Docker
]


@pytest.fixture
def temp_repository() -> None:
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some files in the repository to make it look real
        readme_path = os.path.join(temp_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Test Repository\n\nThis is a test repository for mounting tests.")

        # Create a Python file
        py_file_path = os.path.join(temp_dir, "test_file.py")
        with open(py_file_path, "w") as f:
            f.write(
                """
def hello():
    print("Hello, world!")

if __name__ == "__main__":
    hello()
"""
            )

        # Create a mount test marker file that we can use to verify mounting
        mount_test_path = os.path.join(temp_dir, ".mount_test")
        with open(mount_test_path, "w") as f:
            f.write(f"Mount test marker created at {time.time()}")

        yield temp_dir


@pytest.fixture
def stop_containers() -> None:
    """Stop Code Story containers before and after tests."""
    # Stop containers before test
    subprocess.run(["docker-compose", "down"], cwd=os.getcwd(), capture_output=True)

    yield

    # Stop containers after test
    subprocess.run(["docker-compose", "down"], cwd=os.getcwd(), capture_output=True)


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()


class TestRepositoryMounting:
    """Integration tests for repository mounting."""

    def test_mount_verification(self, temp_repository: Any) -> None:
        """Test that the mount verification correctly detects issues."""
        # Skip this test if Docker is not running
        docker_check = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if docker_check.returncode != 0:
            pytest.skip("Docker is not running")

        print(f"\nTesting repository mounting verification with: {temp_repository}")

        # Create container with a known mount point for testing
        container_name = "codestory-mount-test"
        os.path.basename(temp_repository)
        container_path = "/test-mount"

        # Try to stop any existing container first
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

        # Start a simple container (alpine) without mounting the repository
        start_result = subprocess.run(
            ["docker", "run", "-d", "--name", container_name, "alpine", "sleep", "60"],
            capture_output=True,
            text=True,
            check=False,
        )

        print(f"Container start result: {start_result.stdout}")

        # Verify the container is running
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

        # Test case 1: Verify path does NOT exist in container (should fail)
        print("Test 1: Verifying path doesn't exist without mounting")
        path_check = subprocess.run(
            f"docker exec {container_name} sh -c 'test -d {container_path} && echo exists'",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should NOT find the path
        assert (
            "exists" not in path_check.stdout
        ), "Repository path should not be accessible without mounting"
        print("Test 1 passed: Path not accessible without mounting")

        # Now stop the container
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

        # Test case 2: Start container WITH the repository mounted
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

        # Verify the container is running
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

        assert container_name in container_check.stdout, "Test container with mount is not running"

        # Verify path exists in container
        print("Verifying path exists with mounting")
        path_check = subprocess.run(
            f"docker exec {container_name} sh -c 'test -d {container_path} && echo exists'",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should find the path
        assert (
            "exists" in path_check.stdout
        ), f"Repository path not accessible in container even with mounting: {container_path}"
        print("Test 2 passed: Path accessible with mounting")

        # Check if repository is mounted in container by listing contents
        ls_result = subprocess.run(
            ["docker", "exec", container_name, "ls", "-la", container_path],
            capture_output=True,
            text=True,
        )

        print(f"Directory contents in container: {ls_result.stdout}")

        # Verify files are in the mounted repository
        assert (
            "README.md" in ls_result.stdout
        ), f"Repository not mounted correctly: {ls_result.stdout}"
        assert (
            "test_file.py" in ls_result.stdout
        ), f"Repository not mounted correctly: {ls_result.stdout}"
        assert (
            ".mount_test" in ls_result.stdout
        ), f"Repository not mounted correctly: {ls_result.stdout}"

        # Verify mount test file is accessible by reading its content
        cat_result = subprocess.run(
            ["docker", "exec", container_name, "cat", f"{container_path}/.mount_test"],
            capture_output=True,
            text=True,
        )
        assert (
            "Mount test marker created at" in cat_result.stdout
        ), f"Could not read mount test file: {cat_result.stdout}"

        # Verify mount configuration in Docker container
        inspect_result = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{json .Mounts}}"],
            capture_output=True,
            text=True,
        )
        assert (
            temp_repository in inspect_result.stdout
        ), f"Repository not found in Docker mount configuration: {inspect_result.stdout}"

        # Clean up - stop container
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


@pytest.mark.integration
@pytest.mark.docker
class TestCliAutoMount:
    """CLI integration tests for auto mounting with ingest command."""

    def test_cli_mount_verification_function(self, temp_repository: Any) -> None:
        """Test that ingest command correctly verifies container paths."""
        # Skip this test if Docker is not running
        docker_check = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if docker_check.returncode != 0:
            pytest.skip("Docker is not running")

        from io import StringIO
        from unittest.mock import MagicMock

        print(f"\nTesting CLI mount verification with repository: {temp_repository}")

        # Create a mock CLI context and client
        console = Console(file=StringIO())
        mock_client = MagicMock()
        mock_client.base_url = "http://localhost:8000/v1"
        mock_client.start_ingestion.return_value = {"job_id": "test-job-id"}

        cli_context = {
            "client": mock_client,
            "console": console,
            "settings": MagicMock(),
        }

        # Set up test container
        container_name = "codestory-service"  # Use the expected container name

        # Clean up any existing containers
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

        # Start a container with the right name but WITHOUT the repository mounted
        subprocess.run(
            ["docker", "run", "-d", "--name", container_name, "alpine", "sleep", "60"],
            capture_output=True,
        )

        # Verify the container is running
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

        # Test 1: Without auto-mount enabled, the function should detect the unmounted path
        try:
            # This should fail because the path isn't mounted
            with pytest.raises(Exception) as excinfo:
                # First create a Click context with our mocked objects
                from click import Context

                # Create a Click context object
                click_ctx = Context(ingest)
                # Set the obj attribute to our CLI context
                click_ctx.obj = cli_context

                # Execute the command function directly
                start_ingestion(
                    click_ctx,  # Pass the Click context
                    temp_repository,
                    no_progress=True,
                    container=True,  # Force container path
                    path_prefix="/repositories",
                    auto_mount=False,  # Don't auto-mount
                    no_auto_mount=True,  # Explicitly prevent auto-mounting
                )

            # Verify the error mentions the repository path
            print(f"Got expected exception: {excinfo.value!s}")
            output = console.file.getvalue()
            assert "Repository not mounted" in output or "does not exist" in str(
                excinfo.value
            ), f"CLI did not detect missing mount. Output: {output}, Exception: {excinfo.value}"

            print("Test 1 passed: CLI correctly detected unmounted repository")

        finally:
            # Clean up container
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

        # Test 2: Set up a container WITH the repository mounted
        # This emulates what would happen with auto-mount=True
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
            # This should succeed because the path is mounted
            # Reset the console to clear previous output
            console = Console(file=StringIO())
            cli_context["console"] = console

            # First create a Click context with our mocked objects
            from click import Context

            # Create a Click context object
            click_ctx = Context(ingest)
            # Set the obj attribute to our CLI context
            click_ctx.obj = cli_context

            # Execute the command function directly
            start_ingestion(
                click_ctx,  # Pass the Click context
                temp_repository,
                no_progress=True,
                container=True,  # Force container path
                path_prefix="/repositories",
                auto_mount=False,  # Don't auto-mount (not needed as it's already mounted)
                no_auto_mount=True,  # Explicitly prevent auto-mounting
            )

            # Verify the client's start_ingestion was called with the container path
            mock_client.start_ingestion.assert_called_once()
            call_args = mock_client.start_ingestion.call_args[0][0]
            assert container_path in call_args, f"Container path not passed to service: {call_args}"

            print("Test 2 passed: CLI correctly used mounted repository")

        finally:
            # Clean up container
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
