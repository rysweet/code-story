"""Integration test for Neo4j connectivity."""

import pytest
from codestory.config import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector


def test_neo4j_connection():
    """Test that we can connect to Neo4j with the current configuration."""
    # Get settings
    settings = get_settings()
    
    # Create connector
    connector = Neo4jConnector(
        uri=settings.neo4j.uri,
        username=settings.neo4j.username,
        password=settings.neo4j.password.get_secret_value(),
        database=settings.neo4j.database,
    )
    
    # Test connection
    try:
        with connector.get_session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            assert record["test"] == 1
            
        # If we get here, the connection was successful
        assert True
    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j: {e}")