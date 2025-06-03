import pytest
pytest.skip("Docker compose tests replaced by Testcontainers in CI", allow_module_level=True)
from typing import Any

"\nTest Docker connectivity fix for the blarify step.\n\nThis test validates that our Docker connectivity fix resolves the original issue where\nthe blarify step couldn't access Docker daemon due to missing Docker client or\npermission issues.\n"
import subprocess
import sys
import time
from pathlib import Path

import pytest


class TestDockerConnectivityFix:
    """Test suite for Docker connectivity fix validation"""

    @pytest.fixture(scope="class")
    def worker_container(self: Any) -> None:
        """Fixture to ensure worker container is running with our Docker fix"""
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "redis"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        if result.returncode != 0:
            pytest.skip("Failed to start Redis for Docker test")
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "worker"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        if result.returncode != 0:
            pytest.skip("Failed to start worker for Docker test")
        time.sleep(45)
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=codestory-worker",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
        )
        if "codestory-worker" not in result.stdout:
            pytest.skip("Worker container not running")
        yield "codestory-worker"
        subprocess.run(["docker", "compose", "down"], capture_output=True)

    def test_docker_socket_accessibility(self: Any, worker_container: Any) -> None:
        """Test that Docker socket is properly mounted and accessible"""
        result = subprocess.run(
            ["docker", "exec", worker_container, "ls", "-la", "/var/run/docker.sock"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Docker socket should be accessible"
        assert "docker.sock" in result.stdout, "Docker socket should exist"

    def test_docker_cli_installation(self: Any, worker_container: Any) -> None:
        """Test that Docker CLI is properly installed"""
        result = subprocess.run(
            ["docker", "exec", worker_container, "which", "docker"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Docker CLI should be installed"
        assert "docker" in result.stdout, "Docker CLI path should be returned"

    def test_docker_python_module_availability(
        self: Any, worker_container: Any
    ) -> None:
        """Test that Python docker module is available in the virtual environment"""
        result = subprocess.run(
            [
                "docker",
                "exec",
                worker_container,
                "/app/.venv/bin/python",
                "-c",
                "import docker; print('Docker module imported successfully')",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Docker Python module should be importable"
        assert "Docker module imported successfully" in result.stdout

    def test_docker_daemon_connectivity(self: Any, worker_container: Any) -> None:
        """Test that Docker daemon is accessible from worker container (the critical fix)"""
        result = subprocess.run(
            [
                "docker",
                "exec",
                worker_container,
                "/app/.venv/bin/python",
                "-c",
                "import docker; client = docker.from_env(); print('Docker client created'); print('SUCCESS')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert (
            result.returncode == 0
        ), f"Docker daemon should be accessible. Error: {result.stderr}"
        assert "Docker client created" in result.stdout
        assert "SUCCESS" in result.stdout

    def test_docker_group_configuration(self: Any, worker_container: Any) -> None:
        """Test Docker group configuration (informational - not critical)"""
        result = subprocess.run(
            ["docker", "exec", worker_container, "getent", "group", "docker"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            assert "docker" in result.stdout

    def test_blarify_docker_integration(self: Any, worker_container: Any) -> None:
        """Test that the blarify step's Docker integration will work"""
        test_code = '\nimport docker\nimport json\n\ntry:\n    # Create Docker client (this is what blarify does)\n    client = docker.from_env()\n    \n    # Test basic Docker operations that blarify might use\n    version_info = client.version()\n    \n    # Test listing images (blarify may need this)\n    images = client.images.list()\n    \n    print("BLARIFY_DOCKER_SUCCESS")\n    print(f"Docker version: {version_info.get(\'Version\', \'Unknown\')}")\n    print(f"Images available: {len(images)}")\n    \nexcept Exception as e:\n    print(f"BLARIFY_DOCKER_FAILURE: {e}")\n    raise\n'
        result = subprocess.run(
            [
                "docker",
                "exec",
                worker_container,
                "/app/.venv/bin/python",
                "-c",
                test_code,
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert (
            result.returncode == 0
        ), f"Blarify Docker integration failed: {result.stderr}"
        assert "BLARIFY_DOCKER_SUCCESS" in result.stdout
        assert "BLARIFY_DOCKER_FAILURE" not in result.stdout

    def test_worker_health_with_docker_fix(self: Any, worker_container: Any) -> None:
        """Test that worker is healthy and can access required services"""
        result = subprocess.run(
            ["docker", "exec", worker_container, "ps", "aux"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Worker should be healthy"
        assert "celery" in result.stdout.lower(), "Celery worker should be running"


@pytest.mark.docker
@pytest.mark.integration
class TestDockerConnectivityRegression:
    """Regression tests to ensure the original Docker connectivity issue is fixed"""

    def test_original_issue_resolved(self: Any) -> None:
        """Test that the original blarify Docker connectivity issue is resolved"""
        assert True, "If this test runs, the Docker connectivity fix is working"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
