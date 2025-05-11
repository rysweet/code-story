"""Test fixtures for CLI integration tests."""

import os
import tempfile
import time
import subprocess
from typing import Generator, Tuple, Dict, Any

import pytest
from click.testing import CliRunner
import httpx

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
        "markers", "require_service: mark test as requiring a running Code Story service"
    )


@pytest.fixture
def running_service(request) -> Generator[Dict[str, Any], None, None]:
    """
    Ensures the Code Story service is running for integration tests.

    If the service is already running, uses the existing instance.
    Otherwise, skips the test with an appropriate message.

    Yields:
        Dictionary with service information (url, port, etc.)
    """
    settings = get_settings()
    service_url = f"http://localhost:{settings.service.port}"
    health_url = f"{service_url}/v1/health"

    # Check if service is already running
    try:
        response = httpx.get(f"{health_url}", timeout=2.0)
        if response.status_code == 200:
            # Service is running, use it
            yield {
                "url": service_url,
                "port": settings.service.port,
                "api_url": f"{service_url}/v1"
            }
            return
    except httpx.RequestError:
        pytest.skip(
            "No running Code Story service detected. "
            "Please start the service manually to run integration tests."
        )


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
            f.write("""
def main():
    print("Hello world!")

if __name__ == "__main__":
    main()
""")
        
        with open(os.path.join(temp_dir, "src", "utils.py"), "w") as f:
            f.write("""
def helper_function():
    return "Helper function"
""")
        
        with open(os.path.join(temp_dir, "docs", "README.md"), "w") as f:
            f.write("""
# Test Repository

This is a test repository for Code Story CLI integration tests.
""")
        
        yield temp_dir