"""Test fixtures for CLI integration tests."""
import os
import subprocess
import tempfile
import time
from collections.abc import Generator
from typing import Any

import pytest, docker, uuid, time, os, requests

@pytest.fixture(scope="session", autouse=True)
def ensure_docker_daemon():
    try:
        with docker.from_env() as c:
            c.ping()
    except docker.errors.DockerException:
        pytest.skip("Docker daemon unavailable on host")

@pytest.fixture(scope="session", autouse=True)
def service_container(redis_container, celery_worker_container):
    import docker, subprocess, sys
    client = docker.from_env()
    try:
        name = f"cs-svc-{uuid.uuid4()}"
        container = client.containers.run(
            "python:3.11-slim",
            name=name,
            command=["bash","-c",
                     "pip install -q -e . && uvicorn codestory_service.main:app "
                     "--host 0.0.0.0 --port 8000 --log-level warning"],
            volumes={os.getcwd(): {"bind": "/app", "mode": "rw"}},
            working_dir="/app",
            environment={
                "REDIS_URL": "redis://localhost:6379/0",
                "CELERY_BROKER_URL": "redis://localhost:6379/0",
                "CELERY_RESULT_BACKEND": "redis://localhost:6379/0",
            },
            network_mode="host",
            detach=True,
            auto_remove=True,
        )
        # Wait /health
        for _ in range(60):
            try:
                if requests.get("http://localhost:8000/health").status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            container.kill()
            pytest.skip("Service container unhealthy")

        os.environ["CODESTORY_API_URL"] = "http://localhost:8000"
        os.environ["CODESTORY_API_KEY"] = "dummy-test-key"
        yield
        container.kill()
    finally:
        client.close()

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

@pytest.fixture(autouse=True)
def set_api_url(monkeypatch):
    # FastAPI service_container listens on host port 8000
    monkeypatch.setenv("CODESTORY_API_URL", "http://localhost:8000")
    # Provide dummy API key env var if CLI requires it
    monkeypatch.setenv("CODESTORY_API_KEY", "dummy-test-key")

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


# Removed running_service fixture and all docker-compose/port-mapping logic.
# Integration tests now rely on environment variables set by container fixtures.


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
