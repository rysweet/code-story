from typing import Any
"""Test for the config API."""

import os

# Determine Neo4j port based on CI environment
ci_env = os.environ.get("CI") == "true"
neo4j_port = "7687" if ci_env else "7688"
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
    # Create a connector that uses the Neo4j test container
    connector = Neo4jConnector(
        uri=f"bolt://localhost:{neo4j_port}",  # Port defined in docker-compose.test.yml
        username="neo4j",
        password="password",
        database="testdb",  # Database defined in docker-compose.test.yml
    )

    try:
        # Clear the database to ensure a clean state
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True)

        # Initialize schema (this creates necessary indexes and constraints)
        initialize_schema(connector, force=True)

        print("Successfully connected to Neo4j test database")

        yield connector
    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j test database: {e!s}")
    finally:
        # Clean up after test
        connector.close()


@pytest.fixture
def test_client(neo4j_connector: Any):
    """Create a test client for the FastAPI application."""
    # Set up test environment variables
    os.environ["CODESTORY_SERVICE_DEV_MODE"] = "true"
    os.environ["CODESTORY_SERVICE_AUTH_ENABLED"] = "false"

    # Set up test environment variables for Neo4j
    os.environ["NEO4J_DATABASE"] = "testdb"
    os.environ["CS_NEO4J_DATABASE"] = "testdb"
    os.environ["NEO4J_URI"] = f"bolt://localhost:{neo4j_port}"
    os.environ["CS_NEO4J_URI"] = f"bolt://localhost:{neo4j_port}"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["CS_NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["CS_NEO4J_PASSWORD"] = "password"

    # Also set these for internal services and components
    os.environ["GRAPHDB_DATABASE"] = "testdb"
    os.environ["CODESTORY_NEO4J_DATABASE"] = "testdb"

    # Create a test user instance for authentication
    test_user = {
        "sub": "test-user-id",
        "name": "Test User",
        "email": "test@example.com",
        "roles": ["admin"],
        "exp": int(time.time()) + 3600,
    }

    # Function to return our test user for auth
    async def get_test_user():
        return test_user

    # Store original auth dependency to restore later
    original_auth_dependency = global_app.dependency_overrides.get(get_current_user, None)

    # Override the auth dependency to bypass authentication
    global_app.dependency_overrides[get_current_user] = get_test_user

    # Create a custom lifespan
    @asynccontextmanager
    async def test_lifespan(app):
        # Explicitly set the database name
        neo4j_connector.database = "testdb"
        app.state.db = neo4j_connector
        yield

    # Set up the app with our custom lifespan
    app = create_app()
    app.dependency_overrides[get_current_user] = get_test_user
    app.dependency_overrides[create_app.__globals__["lifespan"]] = test_lifespan

    # Mock the external OpenAI service
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

        # Ensure any new Neo4j connectors use the test database
        os.environ["NEO4J_DATABASE"] = "testdb"

        test_client = TestClient(app)
        yield test_client

        # Clean up
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(create_app.__globals__["lifespan"], None)

        # Restore the original auth dependency
        if original_auth_dependency:
            global_app.dependency_overrides[get_current_user] = original_auth_dependency
        else:
            global_app.dependency_overrides.pop(get_current_user, None)

        # Clean up environment variables
        os.environ.pop("CODESTORY_SERVICE_DEV_MODE", None)
        os.environ.pop("CODESTORY_SERVICE_AUTH_ENABLED", None)


@pytest.mark.integration
def test_config_api_simple(test_client: Any) -> None:
    """Test the configuration API endpoints with basic validation."""
    # Ensure DB is configured correctly for any new connectors
    os.environ["NEO4J_DATABASE"] = "testdb"

    # Test GET /v1/config
    response = test_client.get("/v1/config")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "groups" in data
    assert isinstance(data["groups"], dict)

    # Just verify we can access the config data
    if data["groups"]:
        # Verify we can access the first group
        first_group_name = next(iter(data["groups"]))
        assert first_group_name is not None

        # Print out the group structure to help with debugging
        print(f"Found group: {first_group_name}")
        print(f"Group structure: {data['groups'][first_group_name]}")
