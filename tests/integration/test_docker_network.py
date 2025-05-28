"""Integration tests for Docker container network communication.

This module contains tests that specifically validate the communication between
containers in the Docker network, ensuring that services can correctly 
communicate with each other using the service names as hostnames.
"""

import json
import subprocess
import time
from collections.abc import Generator
from typing import Any

import pytest


@pytest.fixture(scope="module")
def docker_compose_project() -> Generator[dict[str, Any], None, None]:
    """Spin up the Docker Compose project for testing.

    This fixture starts the Docker Compose services, runs the tests,
    and then tears down the services.

    Yields:
        Dictionary with Docker Compose project information
    """
    try:
        # Start containers
        result = subprocess.run(
            ["docker-compose", "up", "-d"], capture_output=True, text=True, check=True
        )
        print(f"Docker Compose started: {result.stdout}")

        # Give services time to start (this could be made more intelligent with health checks)
        time.sleep(10)

        # Get container info
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )

        try:
            containers = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Handle older docker-compose versions that don't support JSON output
            containers = result.stdout

        yield {"containers": containers}

    finally:
        # Tear down containers but keep logs
        subprocess.run(
            ["docker-compose", "logs", "--no-color"], capture_output=True, text=True
        )

        subprocess.run(["docker-compose", "down"], capture_output=True, text=True)


def exec_in_container(container_name: str, command: list[str]) -> dict[str, Any]:
    """Execute a command in a container and return stdout/stderr.

    Args:
        container_name: Name of the container to execute in
        command: Command to execute as a list of strings

    Returns:
        Dictionary with exit_code, stdout, and stderr
    """
    result = subprocess.run(
        ["docker", "exec", container_name, *command], capture_output=True, text=True
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@pytest.mark.integration
@pytest.mark.docker
def test_service_to_neo4j_connectivity(docker_compose_project):
    """Test that the service container can connect to Neo4j using the container name.

    This test executes commands inside the service container to attempt
    to connect to the Neo4j container using its service name.
    """
    service_container = "codestory-service"

    # Test connecting to Neo4j bolt port
    result = exec_in_container(
        service_container,
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "neo4j:7474"],
    )

    # Should be able to reach Neo4j HTTP interface
    assert result["exit_code"] == 0
    assert (
        "200" in result["stdout"] or "302" in result["stdout"]
    ), f"Expected 200 or 302 status code, got: {result['stdout']}"

    # Also verify bolt port is open
    result = exec_in_container(service_container, ["nc", "-z", "-v", "neo4j", "7687"])

    # Expected exit code for successful connection
    assert (
        result["exit_code"] == 0
    ), f"Failed to connect to Neo4j bolt port: {result['stderr']}"


@pytest.mark.integration
@pytest.mark.docker
def test_service_to_redis_connectivity(docker_compose_project):
    """Test that the service container can connect to Redis using the container name.

    This test executes commands inside the service container to attempt
    to connect to the Redis container using its service name.
    """
    service_container = "codestory-service"

    # Test Redis connectivity from service container
    result = exec_in_container(
        service_container, ["timeout", "5", "redis-cli", "-h", "redis", "ping"]
    )

    assert result["exit_code"] == 0, f"Failed to connect to Redis: {result['stderr']}"
    assert (
        "PONG" in result["stdout"]
    ), f"Redis did not respond with PONG: {result['stdout']}"


@pytest.mark.integration
@pytest.mark.docker
def test_health_endpoint_in_container(docker_compose_project):
    """Test that the health endpoint works inside the container.

    This test executes a curl command inside the service container to check
    the health endpoint, verifying that the internal service is working.
    """
    service_container = "codestory-service"

    # Test internal health endpoint
    result = exec_in_container(
        service_container, ["curl", "-s", "localhost:8000/health"]
    )

    assert (
        result["exit_code"] == 0
    ), f"Failed to connect to health endpoint: {result['stderr']}"

    try:
        health_data = json.loads(result["stdout"])
        assert "status" in health_data, "Health response missing status field"
    except json.JSONDecodeError:
        pytest.fail(f"Health endpoint did not return valid JSON: {result['stdout']}")


@pytest.mark.integration
@pytest.mark.docker
def test_external_health_endpoint(docker_compose_project):
    """Test that the health endpoint is accessible from outside the container.

    This test uses the host system to send a request to the exposed service port,
    verifying that the external port mapping works correctly.
    """
    # The port mapping is defined in docker-compose.yml
    service_port = 8000  # This should match what's in docker-compose.yml

    # Try both health endpoints
    for endpoint in ["/health", "/v1/health"]:
        result = subprocess.run(
            ["curl", "-s", f"http://localhost:{service_port}{endpoint}"],
            capture_output=True,
            text=True,
        )

        assert (
            result.returncode == 0
        ), f"Failed to connect to external health endpoint: {result.stderr}"

        try:
            health_data = json.loads(result.stdout)
            assert (
                "status" in health_data
            ), f"Health response missing status field in endpoint {endpoint}"
        except json.JSONDecodeError:
            pytest.fail(
                f"Health endpoint {endpoint} did not return valid JSON: {result.stdout}"
            )
