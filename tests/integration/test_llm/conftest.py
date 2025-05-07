"""Configuration and fixtures for OpenAI integration tests."""

import os
import pytest
from typing import Dict, Any, Generator

from src.codestory.llm.client import OpenAIClient


def pytest_addoption(parser):
    """Add options for integration tests."""
    parser.addoption(
        "--run-openai",
        action="store_true",
        default=False,
        help="Run tests that require OpenAI API access",
    )


def pytest_collection_modifyitems(config, items):
    """Skip OpenAI tests unless explicitly enabled."""
    if not config.getoption("--run-openai"):
        skip_openai = pytest.mark.skip(reason="Need --run-openai option to run")
        for item in items:
            if "openai" in item.keywords:
                item.add_marker(skip_openai)


@pytest.fixture(scope="session")
def openai_credentials() -> Dict[str, Any]:
    """Get OpenAI credentials from environment variables."""
    api_key = os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT") or "https://api.openai.com/v1"
    
    if not api_key:
        pytest.skip("OpenAI API credentials not available")
    
    return {
        "api_key": api_key,
        "endpoint": endpoint,
    }