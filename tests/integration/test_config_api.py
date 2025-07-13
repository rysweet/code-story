# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

import pytest

# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

from typing import Any
import os
import time
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.graphdb.schema import initialize_schema
from codestory_service.infrastructure.msal_validator import get_current_user

# Use unified_test_env for all service configuration
pytestmark = pytest.mark.usefixtures("unified_test_env")

def is_host_native_mode() -> bool:
    """Host-native mode is deprecated. All tests now use containerized services."""
    return False

# Removed custom neo4j_connector fixture; use environment provided by conftest.py


@pytest.fixture
def test_client(unified_test_env) -> TestClient:
    """
    Create a test client for the FastAPI application using unified_test_env for all service configuration.
    """
    # Set environment variables for the test session
    from tests.conftest import get_test_config
    config = get_test_config()
    config.update(unified_test_env)

    from codestory_service.main import app as global_app
    from codestory_service.main import create_app

    test_user = {
        "sub": "test-user-id",
        "name": "Test User",
        "email": "test@example.com",
        "roles": ["admin"],
        "exp": int(time.time()) + 3600,
    }

    async def get_test_user():
        return test_user

    original_auth_dependency = global_app.dependency_overrides.get(get_current_user, None)
    global_app.dependency_overrides[get_current_user] = get_test_user

    @asynccontextmanager
    async def test_lifespan(app):
        yield

    app = create_app()
    app.dependency_overrides[get_current_user] = get_test_user
    app.dependency_overrides[create_app.__globals__["lifespan"]] = test_lifespan

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(create_app.__globals__["lifespan"], None)
    if original_auth_dependency:
        global_app.dependency_overrides[get_current_user] = original_auth_dependency
    else:
        global_app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.integration
def test_config_api_simple(test_client: Any) -> None:
    """Test the configuration API endpoints with basic validation."""
    response = test_client.get("/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "groups" in data
    assert isinstance(data["groups"], dict)
    if data["groups"]:
        first_group_name = next(iter(data["groups"]))
        assert first_group_name is not None
        print(f"Found group: {first_group_name}")
        print(f"Group structure: {data['groups'][first_group_name]}")
