"""Test fixtures for CLI integration tests."""

# Reuse shared infrastructure fixtures from integration/conftest.py
from tests.integration.conftest import (
    redis_container,
    celery_worker_container,
    neo4j_container,
    service_container as _svc,
)

# Re-export for CLI tests
service_container = _svc

import pytest

@pytest.fixture(scope="session")
def running_service(_svc):  # Alias expected by older CLI tests
    """Alias for backward-compatibility; returns the started service container name."""
    return _svc

import os
import subprocess
import tempfile
import time
from collections.abc import Generator
from typing import Any

import pytest

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
