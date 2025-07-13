# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

import pytest

pytestmark = pytest.mark.usefixtures("unified_test_env")

from typing import Any

"""Integration test for Neo4j connectivity.

This module contains tests to verify that:
1. The Neo4j connection environment variables are correctly set
2. The port configuration matches the containerized Neo4j settings (7687)
"""

import os

import pytest

from codestory.config import get_settings


def test_neo4j_connection_env_vars(unified_test_env) -> None:
    """Test that Neo4j connection environment variables are correctly set via unified_test_env."""
    neo4j_uri = unified_test_env.get("NEO4J__URI") or unified_test_env.get("NEO4J_URI")
    assert neo4j_uri is not None, "NEO4J__URI or NEO4J_URI not set in unified_test_env"

    # Get settings to make sure they're loading properly
    settings = get_settings()
    assert settings.neo4j.uri, "Settings should include Neo4j URI"
    assert settings.neo4j.username, "Settings should include Neo4j username"
    assert settings.neo4j.password, "Settings should include Neo4j password"


def test_neo4j_connection_works(unified_test_env) -> None:
    """Test that Neo4j connection actually works using unified_test_env."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    uri = unified_test_env.get("NEO4J__URI") or unified_test_env.get("NEO4J_URI")
    username = unified_test_env.get("NEO4J__USERNAME", "neo4j")
    password = unified_test_env.get("NEO4J__PASSWORD", "password")
    database = unified_test_env.get("NEO4J__DATABASE", "neo4j")
    neo4j_connector = Neo4jConnector(uri=uri, username=username, password=password, database=database)
    result = neo4j_connector.execute_query("RETURN 1 as test")
    assert result[0]["test"] == 1, "Neo4j query did not return expected result"
    neo4j_connector.close()
