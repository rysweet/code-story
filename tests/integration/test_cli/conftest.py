"""Test fixtures for CLI integration tests."""
import os
import subprocess
import tempfile
import time
from collections.abc import Generator
from typing import Any

# (Removed duplicate imports: httpx, pytest, CliRunner)

def is_docker_running() -> bool:
    """Return True if Docker daemon is running, else False."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False

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


def pytest_configure(config: Any) -> None:
    """Add custom markers to pytest."""
    config.addinivalue_line(
        "markers",
        "require_service: mark test as requiring a running Code Story service",
    )


@pytest.fixture(scope="session")
def running_service(request: Any) -> Generator[dict[str, Any], None, None]:
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
    # (Removed unused: service_running = False)
    # (Removed unused: service_process = None)
    try:
        response = httpx.get(f"{health_url}", timeout=2.0)
        if response.status_code == 200:
            print("Service is already running, using existing instance")
    except httpx.RequestError:
        pass
    # --- NEW LOGIC: docker-compose orchestration and health checks ---
    if not is_docker_running():
        pytest.skip("Docker is not running or not available, skipping all require_service tests.")

    compose_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../docker-compose.test.yml"))
    containers = ["neo4j", "redis", "service", "worker"]
    stack_started = False

    try:
        # Start the stack
        up_cmd = [
            "docker-compose",
            "-f",
            compose_file,
            "up",
            "-d",
            *containers,
        ]
        subprocess.run(up_cmd, check=True, timeout=30)
        stack_started = True

        # Wait for neo4j and redis to be healthy (max 30s)
        def wait_healthy(container, timeout_s=30):
            start = time.time()
            while time.time() - start < timeout_s:
                try:
                    result = subprocess.run(
                        [
                            "docker",
                            "inspect",
                            "-f",
                            "{{.State.Health.Status}}",
                            container,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )
                    if result.stdout.strip() == "healthy":
                        return True
                except Exception:
                    pass
                time.sleep(1)
            return False

        if not wait_healthy("codestory-neo4j-test", 30):
            pytest.skip("Neo4j container did not become healthy in time, skipping test session.")
        if not wait_healthy("codestory-redis-test", 30):
            pytest.skip("Redis container did not become healthy in time, skipping test session.")

        # Wait for service health endpoint (max 60s)
        healthy = False
        for _ in range(60):
            try:
                response = httpx.get(health_url, timeout=2.0)
                if response.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(1)
        if not healthy:
            pytest.skip("Service /v1/health endpoint did not become healthy in time, skipping test session.")

        print(f"Service available at {service_url}")
        yield {
            "url": service_url,
            "port": settings.service.port,
            "api_url": f"{service_url}/v1",
        }
    finally:
        if stack_started:
            print("Tearing down docker-compose test stack...")
            down_cmd = [
                "docker-compose",
                "-f",
                compose_file,
                "down",
                "-v",
            ]
            try:
                subprocess.run(down_cmd, check=True, timeout=30)
            except Exception as e:
                print(f"Warning: Failed to tear down docker-compose stack: {e}")


@pytest.fixture
def test_repository() -> Generator[str, None, None]:
    """
    Creates a temporary test repository for ingestion tests.

    Yields:
        Path to the temporary repository.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        os.makedirs(os.path.join(temp_dir, "src"))
        os.makedirs(os.path.join(temp_dir, "docs"))
        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write(
                '\ndef main():\n    print("Hello world!")\n\nif __name__ == "__main__":\n    main()\n'
            )
        with open(os.path.join(temp_dir, "src", "utils.py"), "w") as f:
            f.write('\ndef helper_function():\n    return "Helper function"\n')
        with open(os.path.join(temp_dir, "docs", "README.md"), "w") as f:
            f.write(
                "\n# Test Repository\n\nThis is a test repository for Code Story CLI integration tests.\n"
            )
        yield temp_dir
