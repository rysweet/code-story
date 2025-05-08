import pytest
from codestory.graphdb.neo4j_connector import Neo4jConnector

@pytest.fixture(scope="module")
def connector():
    # Use the non-standard port as configured in docker-compose.yaml
    uri = "bolt://localhost:17687"
    username = "neo4j"
    password = "testpassword"
    conn = Neo4jConnector(uri=uri, username=username, password=password)
    yield conn
    conn.close()
