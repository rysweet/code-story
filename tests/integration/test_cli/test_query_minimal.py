# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md
# Centralized Test Configuration Standard:
#   - All test configuration and environment variable access must use get_test_config() from tests/conftest.py.
#   - Manual or direct os.environ usage is forbidden in test modules.
#   - See tests/conftest.py for documentation, priority order, and usage examples.

from tests.conftest import get_test_config
import pytest
import time

@pytest.mark.usefixtures("unified_test_env")
def test_neo4j_connection_and_query():
    """Test minimal Neo4j connection and query using unified_test_env."""
    from neo4j import GraphDatabase
    config = get_test_config()
    uri = config.get("CODESTORY_NEO4J__URI") or config.get("NEO4J_URI")
    username = config.get("CODESTORY_NEO4J__USERNAME") or config.get("NEO4J_USERNAME", "neo4j")
    password = config.get("CODESTORY_NEO4J__PASSWORD") or config.get("NEO4J_PASSWORD") or "password"
    driver = GraphDatabase.driver(uri, auth=(username, password))
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as count LIMIT 5")
        count = result.single()["count"]
        assert isinstance(count, int)
    driver.close()