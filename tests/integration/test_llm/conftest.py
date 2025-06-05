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


# Skipping logic removed: All OpenAI integration tests must run by default.


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
        # Provide dummy endpoint for xfail logic in tests
        endpoint = "https://dummy.openai.endpoint"
    sub_id = os.environ.get("OPENAI__SUBSCRIPTION_ID") or os.environ.get(
        "AZURE_SUBSCRIPTION_ID"
    )
    return {
        "endpoint": endpoint,
        "tenant_id": os.environ.get("OPENAI__TENANT_ID")
        or os.environ.get("AZURE_TENANT_ID"),
        "subscription_id": sub_id or "dummy-subscription",
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
        # If tenant is not correct, just continue; test will xfail if real call is attempted
        if subscription_id:
            subprocess.run(
                ["az", "account", "set", "--subscription", subscription_id],
                check=False,
                capture_output=True,
            )
    except Exception:
        # Do not skip; test will xfail if real call is attempted
        pass


import contextlib

@pytest.fixture
def client(openai_credentials: Any, azure_login: Any):
    """Create an OpenAI client for testing, and ensure it is closed after use."""
    try:
        client = create_client()
    except Exception:
        class DummyClient:
            def __getattr__(self, name):
                raise RuntimeError("OpenAI client could not be created (missing credentials or config)")
        client = DummyClient()
    yield client
    import gc
    if hasattr(client, "close"):
        with contextlib.suppress(Exception):
            client.close()
    # Try to close underlying HTTPX/requests session if present
    for attr in ("_sync_client", "_async_client"):
        obj = getattr(client, attr, None)
        if obj is not None:
            for subattr in ("close", "aclose"):
                fn = getattr(obj, subattr, None)
                if callable(fn):
                    with contextlib.suppress(Exception):
                        fn()
            # Try to close .session or .transport if present
            for subattr in ("session", "transport"):
                subobj = getattr(obj, subattr, None)
                if hasattr(subobj, "close") and callable(subobj.close):
                    with contextlib.suppress(Exception):
                        subobj.close()
    gc.collect()
