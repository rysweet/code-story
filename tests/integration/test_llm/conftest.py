"""Configuration and fixtures for OpenAI API integration tests."""
import os
import subprocess
from typing import Any

import pytest

from codestory.config.settings import get_settings, refresh_settings
from codestory.llm.client import OpenAIClient, create_client


def pytest_addoption(parser: Any) -> None:
    """Add command line options for integration tests."""
    parser.addoption(
        "--skip-openai",
        action="store_true",
        default=False,
        help="Skip tests that require OpenAI API access",
    )
    parser.addoption(
        "--run-openai",
        action="store_true",
        default=False,
        help="[DEPRECATED] Use --skip-openai=False instead",
    )


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line(
        "markers", "openai: mark test as requiring OpenAI API access"
    )


def pytest_collection_modifyitems(config: Any, items: Any) -> None:
    """Skip OpenAI tests if explicitly disabled or if they require Azure.

    For Azure tests, we first check if Azure credentials are available before skipping.
    """
    skip_openai = pytest.mark.skip(
        reason="Tests using OpenAI are disabled with --skip-openai"
    )
    should_skip_openai = config.getoption("--skip-openai") or not config.getoption(
        "--run-openai"
    )
    if should_skip_openai:
        for item in items:
            if "openai" in item.keywords:
                item.add_marker(skip_openai)


@pytest.fixture(scope="session")
def openai_credentials() -> dict[str, Any]:
    """Get OpenAI credentials from environment variables."""
    import contextlib

    with contextlib.suppress(Exception):
        refresh_settings()
    try:
        settings = get_settings()
        endpoint = settings.openai.endpoint
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
    endpoint = os.environ.get("OPENAI__ENDPOINT") or os.environ.get(
        "AZURE_OPENAI_ENDPOINT"
    )
    if not endpoint:
        pytest.skip("No OpenAI API endpoint found in environment")
    sub_id = os.environ.get("OPENAI__SUBSCRIPTION_ID") or os.environ.get(
        "AZURE_SUBSCRIPTION_ID"
    )
    return {
        "endpoint": endpoint,
        "tenant_id": os.environ.get("OPENAI__TENANT_ID")
        or os.environ.get("AZURE_TENANT_ID"),
        "subscription_id": sub_id,
        "embedding_model": os.environ.get(
            "OPENAI__EMBEDDING_MODEL", "text-embedding-3-small"
        ),
        "chat_model": os.environ.get("OPENAI__CHAT_MODEL", "gpt-4o"),
        "reasoning_model": os.environ.get("OPENAI__REASONING_MODEL", "gpt-4o"),
    }


@pytest.fixture
def azure_login(openai_credentials: Any) -> None:
    """Ensure Azure CLI is logged in to the correct tenant."""
    tenant_id = openai_credentials.get("tenant_id")
    subscription_id = openai_credentials.get("subscription_id")
    if not tenant_id:
        return
    try:
        tenant_result = subprocess.run(
            ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
            check=False,
            capture_output=True,
            text=True,
        )
        current_tenant = (
            tenant_result.stdout.strip() if tenant_result.returncode == 0 else None
        )
        if tenant_result.returncode != 0 or current_tenant != tenant_id:
            pytest.skip(
                f"Azure CLI not logged into the correct tenant. Run:\naz login --tenant {tenant_id}"
            )
        if subscription_id:
            subprocess.run(
                ["az", "account", "set", "--subscription", subscription_id],
                check=False,
                capture_output=True,
            )
    except Exception:
        pytest.skip("Failed to verify Azure CLI login status")


@pytest.fixture
def client(openai_credentials: Any, azure_login: Any) -> OpenAIClient:
    """Create an OpenAI client for testing."""
    try:
        return create_client()
    except Exception as e:
        pytest.skip(f"Failed to create OpenAI client: {e}")
