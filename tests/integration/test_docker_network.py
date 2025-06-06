import pytest

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
    """
    Spin up the Docker Compose project for testing, robustly waiting for all services to be healthy.
    Yields:
        Dictionary with Docker Compose project information
    """
    import shutil

    compose_file = "docker-compose.test.yml"
    required_services = ["neo4j", "redis", "service", "worker"]
    max_wait = 120  # seconds
    poll_interval = 3

    if not shutil.which("docker-compose"):
        pytest.skip("docker-compose is not installed")

    try:
        # Start containers using test compose file
        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "up", "-d"],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
        print(f"Docker Compose started: {result.stdout}")

        # Poll for all required services to be healthy
        start = time.time()
        healthy = {s: False for s in required_services}
        print("Polling for service health...")
        while time.time() - start < max_wait:
            ps = subprocess.run(
                ["docker-compose", "-f", compose_file, "ps", "--format", "json"],
                capture_output=True,
                text=True,
            )
            try:
                containers = json.loads(ps.stdout)
            except Exception:
                containers = []
            for c in containers:
                name = c.get("Name") or c.get("Service")
                health = c.get("Health") or c.get("State")
                if name in healthy and health and "healthy" in health:
                    healthy[name] = True
            if all(healthy.values()):
                print("All services healthy.")
                break
            time.sleep(poll_interval)
        else:
            # Print logs for debugging
            logs = subprocess.run(
                ["docker-compose", "-f", compose_file, "logs", "--no-color"],
                capture_output=True,
                text=True,
            )
            print(f"Service logs:\n{logs.stdout}")
            raise RuntimeError(f"Not all services became healthy in {max_wait}s: {healthy}")

        # Get final container info
        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "ps", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        try:
            containers = json.loads(result.stdout)
        except json.JSONDecodeError:
            containers = result.stdout

        yield {"containers": containers}

    except subprocess.TimeoutExpired:
        print("Timeout starting Docker containers")
        raise
    finally:
        # Tear down containers but keep logs
        subprocess.run(
            ["docker-compose", "-f", compose_file, "logs", "--no-color"],
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["docker-compose", "-f", compose_file, "down"],
            capture_output=True,
            text=True,
        )


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
def test_service_to_neo4j_connectivity(docker_compose_project: Any) -> None:
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
def test_service_to_redis_connectivity(docker_compose_project: Any) -> None:
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
def test_health_endpoint_in_container(docker_compose_project: Any) -> None:
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
def test_external_health_endpoint(docker_compose_project: Any) -> None:
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
