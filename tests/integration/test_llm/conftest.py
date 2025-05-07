"""Configuration and fixtures for OpenAI API integration tests."""

import os
import subprocess
from typing import Any

import pytest

from src.codestory.config.settings import get_settings, refresh_settings
from src.codestory.llm.client import OpenAIClient, create_client


def pytest_addoption(parser):
    """Add command line options for integration tests."""
    parser.addoption(
        "--run-openai",
        action="store_true",
        default=False,
        help="Run tests that require OpenAI API access"
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "openai: mark test as requiring OpenAI API access")


def pytest_collection_modifyitems(config, items):
    """Skip OpenAI tests unless explicitly enabled."""
    if not config.getoption("--run-openai"):
        skip_openai = pytest.mark.skip(reason="Need --run-openai option to run")
        for item in items:
            if "openai" in item.keywords:
                item.add_marker(skip_openai)


@pytest.fixture(scope="session")
def openai_credentials() -> dict[str, Any]:
    """Get OpenAI credentials from environment variables."""
    # Try to refresh settings
    import contextlib
    with contextlib.suppress(Exception):
        refresh_settings()
    
    # First try loading from settings
    try:
        settings = get_settings()
        
        # Check for endpoint
        endpoint = settings.openai.endpoint
        
        # Return credentials
        return {
            "endpoint": endpoint,
            "tenant_id": getattr(settings.openai, "tenant_id", None),
            "subscription_id": getattr(settings.openai, "subscription_id", None),
            "embedding_model": settings.openai.embedding_model,
            "chat_model": settings.openai.chat_model,
            "reasoning_model": settings.openai.reasoning_model,
        }
    except Exception:
        pass
    
    # Fall back to environment variables
    endpoint = os.environ.get("OPENAI__ENDPOINT") or os.environ.get("AZURE_OPENAI_ENDPOINT")
    
    if not endpoint:
        pytest.skip("No OpenAI API endpoint found in environment")
    
    sub_id = (os.environ.get("OPENAI__SUBSCRIPTION_ID") or 
              os.environ.get("AZURE_SUBSCRIPTION_ID"))
    
    return {
        "endpoint": endpoint,
        "tenant_id": os.environ.get("OPENAI__TENANT_ID") or os.environ.get("AZURE_TENANT_ID"),
        "subscription_id": sub_id,
        "embedding_model": os.environ.get("OPENAI__EMBEDDING_MODEL", "text-embedding-3-small"),
        "chat_model": os.environ.get("OPENAI__CHAT_MODEL", "gpt-4o"),
        "reasoning_model": os.environ.get("OPENAI__REASONING_MODEL", "gpt-4o"),
    }


@pytest.fixture
def azure_login(openai_credentials) -> None:
    """Ensure Azure CLI is logged in to the correct tenant."""
    tenant_id = openai_credentials.get("tenant_id")
    subscription_id = openai_credentials.get("subscription_id")
    
    if not tenant_id:
        return
    
    try:
        # Check current tenant
        tenant_result = subprocess.run(
            ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
            check=False,
            capture_output=True,
            text=True
        )
        
        current_tenant = tenant_result.stdout.strip() if tenant_result.returncode == 0 else None
        
        # If tenant doesn't match, suggest login
        if tenant_result.returncode != 0 or current_tenant != tenant_id:
            pytest.skip(
                f"Azure CLI not logged into the correct tenant. Run:\n"
                f"az login --tenant {tenant_id}"
            )
        
        # Set subscription if provided
        if subscription_id:
            subprocess.run(
                ["az", "account", "set", "--subscription", subscription_id],
                check=False,
                capture_output=True
            )
    except Exception:
        pytest.skip("Failed to verify Azure CLI login status")


@pytest.fixture
def client(openai_credentials, azure_login) -> OpenAIClient:
    """Create an OpenAI client for testing."""
    try:
        # Create client from settings
        return create_client()
    except Exception as e:
        pytest.skip(f"Failed to create OpenAI client: {e}")