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
from codestory_service.main import app as global_app
from codestory_service.main import create_app


@pytest.fixture(scope="module")
def neo4j_connector() -> None:
    """Create a Neo4j connector for integration tests."""
    connector = Neo4jConnector(
        uri=os.environ["NEO4J_URI"],
        username="neo4j",
        password="password",
        database="neo4j",
    )
    try:
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        initialize_schema(connector, force=True)
        print("Successfully connected to Neo4j test database")
        yield connector
    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j test database: {e!s}")
    finally:
        connector.close()


@pytest.fixture
def test_client(neo4j_connector: Any) -> None:
    """Create a test client for the FastAPI application."""
    os.environ["CODESTORY_SERVICE_DEV_MODE"] = "true"
    os.environ["CODESTORY_SERVICE_AUTH_ENABLED"] = "false"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    os.environ["CS_NEO4J_DATABASE"] = "neo4j"
    neo4j_uri = os.environ["NEO4J_URI"]
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["CS_NEO4J_URI"] = neo4j_uri
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

    original_auth_dependency = global_app.dependency_overrides.get(
        get_current_user, None
    )
    global_app.dependency_overrides[get_current_user] = get_test_user

    @asynccontextmanager
    async def test_lifespan(app) -> None:
        neo4j_connector.database = "neo4j"
        app.state.db = neo4j_connector
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
