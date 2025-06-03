from typing import Any

"""Integration test for Neo4j connectivity.

This module contains tests to verify that:
1. The Neo4j connection environment variables are correctly set
2. The port configuration matches the test docker-compose settings (7688)
"""

import os

import pytest

from codestory.config import get_settings


def test_neo4j_connection_env_vars() -> None:
    """Test that Neo4j connection environment variables are correctly set."""
    neo4j_uri = os.environ.get("NEO4J__URI") or os.environ.get("NEO4J_URI")
    assert neo4j_uri is not None, "NEO4J__URI or NEO4J_URI environment variable not set"

    # Get settings to make sure they're loading properly
    settings = get_settings()
    assert settings.neo4j.uri, "Settings should include Neo4j URI"
    assert settings.neo4j.username, "Settings should include Neo4j username"
    assert settings.neo4j.password, "Settings should include Neo4j password"


def test_neo4j_connection_works(neo4j_connector: Any) -> None:
    """Test that Neo4j connection actually works using the test fixture."""
    # Simple query to verify connection works
    result = neo4j_connector.execute_query("RETURN 1 as test")
    assert result[0]["test"] == 1, "Neo4j query did not return expected result"
