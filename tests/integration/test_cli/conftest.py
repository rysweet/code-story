"""Test fixtures for CLI integration tests."""

import os
import subprocess
import tempfile
import time
from collections.abc import Generator
from typing import Any

import httpx
import pytest
from click.testing import CliRunner

from codestory.config import get_settings


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    Creates a Click CLI test runner.

    Returns:
        Click CLI test runner.
    """
    return CliRunner()


def pytest_configure(config):
    """Add custom markers to pytest."""
    config.addinivalue_line(
        "markers",
        "require_service: mark test as requiring a running Code Story service",
    )


@pytest.fixture(scope="session")
def running_service(request) -> Generator[dict[str, Any], None, None]:
    """
    Ensures the Code Story service is running for integration tests.

    If the service is already running, uses the existing instance.
    Otherwise, starts the service automatically.

    Yields:
        Dictionary with service information (url, port, etc.)
    """
    import os
    import signal

    settings = get_settings()
    service_url = f"http://localhost:{settings.service.port}"
    health_url = f"{service_url}/v1/health"

    # Check if service is already running
    service_running = False
    service_process = None

    try:
        response = httpx.get(f"{health_url}", timeout=2.0)
        if response.status_code == 200:
            service_running = True
            print("Service is already running, using existing instance")
    except httpx.RequestError:
        pass

    # If service is not running, start it
    if not service_running:
        print("Starting Code Story service for integration tests...")

        # First try the easier approach of letting the CLI handle it
        try:
            print("Attempting to use CLI service management...")
            # Start the service using the CLI command
            subprocess.run(
                ["python", "-m", "codestory.cli.main", "service", "start"],
                check=True,
                timeout=10,
            )

            # Check if it started
            time.sleep(2)
            try:
                response = httpx.get(f"{health_url}", timeout=2.0)
                if response.status_code == 200:
                    service_running = True
                    print("Service started successfully using CLI!")
            except httpx.RequestError:
                pass
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            print(f"CLI service start failed: {e}")

        # If that didn't work, try the direct approach
        if not service_running:
            print("Trying direct service start approach...")
            # Start the Neo4j container if not already running
            try:
                subprocess.run(
                    ["docker-compose", "up", "-d", "neo4j"],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                print("Started Neo4j container")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"Warning: Failed to start Neo4j container: {e}")

            # Wait a bit for Neo4j to start
            time.sleep(5)

            # Start the service directly
            print("Starting service process...")
            try:
                service_process = subprocess.Popen(
                    ["python", "-m", "codestory.service", "start"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid,  # To kill the process group later
                )
            except Exception as e:
                print(f"Failed to start service process: {e}")
                # Try an alternative approach
                try:
                    print("Trying alternative service start...")
                    service_process = subprocess.Popen(
                        [
                            "python",
                            "-m",
                            "codestory.cli.main",
                            "service",
                            "start",
                            "--debug",
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        preexec_fn=os.setsid,  # To kill the process group later
                    )
                except Exception as e:
                    print(f"Failed to start service with alternative approach: {e}")

            # Wait for service to start (up to 45 seconds)
            started = False
            for i in range(45):
                time.sleep(1)
                print(f"Waiting for service to start (attempt {i + 1}/45)...")
                try:
                    response = httpx.get(f"{health_url}", timeout=2.0)
                    if response.status_code == 200:
                        started = True
                        print("Service started successfully!")
                        break
                except httpx.RequestError:
                    pass

            if not started:
                print("Service failed to start in time")
                # Print container logs for debugging
                try:
                    print("--- Neo4j logs ---")
                    subprocess.run(["docker", "logs", "codestory-neo4j-test"], check=False)
                except Exception as e:
                    print(f"Could not get Neo4j logs: {e}")
                try:
                    print("--- Service logs ---")
                    subprocess.run(["docker", "logs", "codestory-service"], check=False)
                except Exception as e:
                    print(f"Could not get service logs: {e}")
                if service_process:
                    print("Terminating service process...")
                    try:
                        if service_process.poll() is None:
                            os.killpg(os.getpgid(service_process.pid), signal.SIGTERM)
                    except (ProcessLookupError, OSError) as e:
                        print(f"Process already terminated: {e}")
                try:
                    response = httpx.get(f"{health_url}", timeout=2.0)
                    if response.status_code == 200:
                        service_running = True
                        print("Service is available despite startup issues!")
                        return
                except httpx.RequestError:
                    pass
                raise Exception("Failed to start Code Story service after multiple attempts")

            # Wait for Redis to be healthy before starting the service
            redis_healthy = False
            for i in range(30):
                try:
                    result = subprocess.run(
                        [
                            "docker",
                            "inspect",
                            "-f",
                            "{{.State.Health.Status}}",
                            "codestory-redis-test",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )
                    if result.stdout.strip() == "healthy":
                        redis_healthy = True
                        print("Redis container is healthy.")
                        break
                    else:
                        print(
                            f"Waiting for Redis to be healthy (attempt {i + 1}/30)... "
                            f"Status: {result.stdout.strip()}"
                        )
                except Exception as e:
                    print(f"Error checking Redis health: {e}")
                time.sleep(1)
            if not redis_healthy:
                print("Redis container did not become healthy in time.")

    # Service is now running
    print(f"Service available at {service_url}")
    yield {
        "url": service_url,
        "port": settings.service.port,
        "api_url": f"{service_url}/v1",
    }

    # Cleanup if we started the service
    if service_process:
        print("Stopping Code Story service...")
        try:
            # Safely terminate the process if it's still running
            if service_process.poll() is None:
                os.killpg(os.getpgid(service_process.pid), signal.SIGTERM)
        except (ProcessLookupError, OSError) as e:
            print(f"Process already terminated: {e}")

        # Also stop any services started with docker-compose
        try:
            subprocess.run(["docker-compose", "stop"], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to stop services: {e}")


@pytest.fixture
def test_repository() -> Generator[str, None, None]:
    """
    Creates a temporary test repository for ingestion tests.

    Yields:
        Path to the temporary repository.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple test repository structure
        os.makedirs(os.path.join(temp_dir, "src"))
        os.makedirs(os.path.join(temp_dir, "docs"))

        # Create a few test files
        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write(
                """
def main():
    print("Hello world!")

if __name__ == "__main__":
    main()
"""
            )

        with open(os.path.join(temp_dir, "src", "utils.py"), "w") as f:
            f.write(
                """
def helper_function():
    return "Helper function"
"""
            )

        with open(os.path.join(temp_dir, "docs", "README.md"), "w") as f:
            f.write(
                """
# Test Repository

This is a test repository for Code Story CLI integration tests.
"""
            )

        yield temp_dir
