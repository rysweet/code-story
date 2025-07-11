import pytest

pytestmark = pytest.mark.usefixtures("test_containers_and_service")

print(f"[IMPORT-TIME] CODESTORY_NEO4J__URI={__import__('os').environ.get('CODESTORY_NEO4J__URI')}, NEO4J_URI={__import__('os').environ.get('NEO4J_URI')}")
from typing import Any

"Test for the config API."
import os

import time
import unittest.mock as mock
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.graphdb.schema import initialize_schema
from codestory_service.infrastructure.msal_validator import get_current_user
# Delay import of settings-dependent modules until after environment is set up by fixtures
# from codestory_service.main import app as global_app
# from codestory_service.main import create_app


def is_host_native_mode() -> bool:
    """Host-native mode is deprecated. All tests now use containerized services."""
    return False

# Removed custom neo4j_connector fixture; use environment provided by conftest.py


@pytest.fixture
def test_client() -> None:
    """Create a test client for the FastAPI application.

    """
    os.environ["CODESTORY_SERVICE_DEV_MODE"] = "true"
    os.environ["CODESTORY_SERVICE_AUTH_ENABLED"] = "false"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    os.environ["CS_NEO4J_DATABASE"] = "neo4j"
    neo4j_uri = os.environ.get("CODESTORY_NEO4J__URI") or os.environ.get("NEO4J_URI")
    if not neo4j_uri:
        pytest.fail(
            "Neo4j URI must be set in environment variable CODESTORY_NEO4J__URI or NEO4J_URI for integration tests."
        )
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["CS_NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["CS_NEO4J_PASSWORD"] = "password"
    os.environ["GRAPHDB_DATABASE"] = "neo4j"
    os.environ["CODESTORY_NEO4J_DATABASE"] = "neo4j"
    test_user = {
        "sub": "test-user-id",
        "name": "Test User",
        "email": "test@example.com",
        "roles": ["admin"],
        "exp": int(time.time()) + 3600,
    }

    async def get_test_user():
        return test_user

    # Delayed import after environment is set up
    from codestory_service.main import app as global_app
    from codestory_service.main import create_app

    # Initialize schema after environment is ready
    connector = Neo4jConnector(
        uri=neo4j_uri,
        username="neo4j",
        password="password",
        database="neo4j",
    )
    try:
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        initialize_schema(connector, force=True)
        print("Successfully connected to Neo4j test database")
    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j test database: {e!s}")
    finally:
        connector.close()

    original_auth_dependency = global_app.dependency_overrides.get(
        get_current_user, None
    )
    global_app.dependency_overrides[get_current_user] = get_test_user

    @asynccontextmanager
    async def test_lifespan(app) -> None:
        yield

    app = create_app()
    app.dependency_overrides[get_current_user] = get_test_user
    app.dependency_overrides[create_app.__globals__["lifespan"]] = test_lifespan
    with mock.patch(
        "codestory_service.infrastructure.openai_adapter.OpenAIAdapter.check_health"
    ) as mock_openai:
        mock_openai.return_value = {
            "status": "healthy",
            "details": {
                "models": {
                    "embedding": "text-embedding-ada-002",
                    "chat": "gpt-4",
                    "reasoning": "gpt-4",
                }
            },
        }
        os.environ["NEO4J_DATABASE"] = "neo4j"
        test_client = TestClient(app)
        yield test_client
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(create_app.__globals__["lifespan"], None)
        if original_auth_dependency:
            global_app.dependency_overrides[get_current_user] = original_auth_dependency
        else:
            global_app.dependency_overrides.pop(get_current_user, None)
        os.environ.pop("CODESTORY_SERVICE_DEV_MODE", None)
        os.environ.pop("CODESTORY_SERVICE_AUTH_ENABLED", None)


@pytest.mark.integration
def test_config_api_simple(test_client: Any) -> None:
    """Test the configuration API endpoints with basic validation."""
    if is_host_native_mode():
        pytest.skip("Skipping test_config_api_simple in host-native mode (no Neo4j backend)")
    os.environ["NEO4J_DATABASE"] = "neo4j"
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
