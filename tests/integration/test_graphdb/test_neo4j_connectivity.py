from typing import Any

"""Integration test for Neo4j connectivity.

This module contains tests to verify that:
1. The Neo4j connection environment variables are correctly set
2. The port configuration matches the test docker-compose settings (7688)
"""

import os

import pytest

from codestory.config import get_settings


@pytest.mark.parametrize("use_env_check", [True])
def test_neo4j_connection_env_vars(use_env_check: Any, test_databases: Any) -> None:
    """Test that Neo4j connection environment variables are correctly set.

    This test focuses on verifying the environment configuration and
    making an actual connection using the test database fixtures.
    """
    # The test_databases fixture should have started the databases and set environment variables
    db_info = test_databases
    
    # Check Neo4j environment variables are set correctly for testing
    neo4j_uri = os.environ.get("NEO4J__URI")
    assert neo4j_uri is not None, "NEO4J__URI environment variable not set"

    # The environment variable should contain the test port 7688
    assert "7688" in neo4j_uri, f"NEO4J__URI should use test port 7688 (got {neo4j_uri})"

    # Get settings to make sure they're loading properly
    settings = get_settings()
    assert settings.neo4j.uri, "Settings should include Neo4j URI"
    assert settings.neo4j.username, "Settings should include Neo4j username"
    assert settings.neo4j.password, "Settings should include Neo4j password"

    # Verify database info from fixture
    assert db_info["neo4j_uri"] == "bolt://localhost:7688"
    assert db_info["neo4j_username"] == "neo4j"
    assert db_info["neo4j_password"] == "password"
    assert db_info["neo4j_database"] == "testdb"


def test_neo4j_connection_works(neo4j_connector: Any) -> None:
    """Test that Neo4j connection actually works using the test fixture."""
    # Simple query to verify connection works
    result = neo4j_connector.execute_query("RETURN 1 as test")
    assert result[0]["test"] == 1, "Neo4j query did not return expected result"
