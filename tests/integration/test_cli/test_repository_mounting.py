"""
Integration tests for repository mounting functionality.

These tests verify that the repository mounting works correctly
with real Docker containers and filesystem access.

Note: These tests require Docker to be running and will interact
with real containers. They may modify your Docker environment.
"""

import os
import sys
import tempfile
import time
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from codestory.cli.commands.ingest import ingest


# Skip these tests if Docker is not available
pytestmark = pytest.mark.skipif(
    subprocess.run(
        ["docker", "ps"], 
        capture_output=True
    ).returncode != 0,
    reason="Docker is not available"
)


@pytest.fixture
def temp_repository():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some files in the repository to make it look real
        readme_path = os.path.join(temp_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Test Repository\n\nThis is a test repository for mounting tests.")
        
        # Create a Python file
        py_file_path = os.path.join(temp_dir, "test_file.py")
        with open(py_file_path, "w") as f:
            f.write("""
def hello():
    print("Hello, world!")

if __name__ == "__main__":
    hello()
""")
        
        yield temp_dir


@pytest.fixture
def stop_containers():
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
    
    def test_auto_mount_script(self, temp_repository, stop_containers):
        """Test that auto_mount.py script correctly mounts a repository."""
        # Get path to auto_mount.py
        auto_mount_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "scripts", "auto_mount.py"
        )
        
        # Run auto_mount.py script
        result = subprocess.run(
            [sys.executable, auto_mount_path, temp_repository, "--no-ingest"],
            capture_output=True,
            text=True
        )
        
        # Check that script ran successfully
        assert result.returncode == 0, f"auto_mount.py failed with output: {result.stderr}"
        
        # Check that repository is mounted
        container_name = "codestory-service"
        repo_name = os.path.basename(temp_repository)
        container_path = f"/repositories/{repo_name}"
        
        # Wait for container to be ready
        for i in range(30):
            container_check = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )
            if container_name in container_check.stdout:
                break
            time.sleep(1)
        
        # Check if repository is mounted in container
        ls_result = subprocess.run(
            ["docker", "exec", container_name, "ls", "-la", container_path],
            capture_output=True,
            text=True
        )
        
        # Verify README.md is in the mounted repository
        assert "README.md" in ls_result.stdout, f"Repository not mounted correctly: {ls_result.stdout}"
        
        # Verify test_file.py is in the mounted repository
        assert "test_file.py" in ls_result.stdout, f"Repository not mounted correctly: {ls_result.stdout}"
        
        # Verify repository config file was created
        config_path = os.path.join(temp_repository, ".codestory", "repository.toml")
        assert os.path.exists(config_path), "Repository config file was not created"
        
        # Stop containers
        subprocess.run(["docker-compose", "down"], cwd=os.getcwd(), capture_output=True)


@pytest.mark.skipif(True, reason="This test requires a running service and can modify Docker state")
class TestCliAutoMount:
    """CLI integration tests for auto mounting with ingest command."""
    
    def test_cli_auto_mount(self, temp_repository, stop_containers, cli_runner):
        """Test that CLI auto-mount feature correctly mounts repositories."""
        # Install package in development mode to make CLI available
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            cwd=os.getcwd(),
            capture_output=True
        )
        
        # Run CLI command with auto-mount
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "src", "codestory", "cli", "run.py"
        )
        
        # Run the CLI command
        result = subprocess.run(
            [sys.executable, cli_path, "ingest", "start", temp_repository, "--auto-mount", "--no-progress"],
            capture_output=True,
            text=True
        )
        
        # Should succeed or at least show that repository was mounted
        assert "Repository successfully mounted" in result.stdout or result.returncode == 0
        
        # Check that repository is mounted
        container_name = "codestory-service"
        repo_name = os.path.basename(temp_repository)
        container_path = f"/repositories/{repo_name}"
        
        # Check if repository is mounted in container
        ls_result = subprocess.run(
            ["docker", "exec", container_name, "ls", "-la", container_path],
            capture_output=True,
            text=True
        )
        
        # Verify files are in the mounted repository
        assert "README.md" in ls_result.stdout, f"Repository not mounted correctly: {ls_result.stdout}"
        assert "test_file.py" in ls_result.stdout, f"Repository not mounted correctly: {ls_result.stdout}"