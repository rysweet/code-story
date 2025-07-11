import os
import pytest
import time

@pytest.mark.usefixtures("test_containers_and_service")
def test_neo4j_connection_and_query():
    from neo4j import GraphDatabase
    uri = os.environ.get("CODESTORY_NEO4J__URI") or os.environ.get("NEO4J_URI")
    username = os.environ.get("CODESTORY_NEO4J__USERNAME") or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("CODESTORY_NEO4J__PASSWORD") or os.environ.get("NEO4J_PASSWORD") or "password"
    print(f"[test_query_minimal] CODESTORY_NEO4J__URI={os.environ.get('CODESTORY_NEO4J__URI')}")
    print(f"[test_query_minimal] NEO4J_URI={os.environ.get('NEO4J_URI')}")
    print(f"[test_query_minimal] Using uri={uri}, username={username}, password={password}")
    # Health check: wait for Neo4j to be ready
    from neo4j.exceptions import ServiceUnavailable
    driver = GraphDatabase.driver(uri, auth=(username, password))
    for attempt in range(30):
        try:
            with driver.session() as session:
                result = session.run("RETURN 1 AS ready")
                if result.single()["ready"] == 1:
                    print("[test_query_minimal] Neo4j is ready.")
                    break
        except ServiceUnavailable as e:
            print(f"[test_query_minimal] Waiting for Neo4j to be ready... ({e})")
            time.sleep(1)
    else:
        pytest.fail("Neo4j did not become ready in time.")
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as count LIMIT 5")
        count = result.single()["count"]
        print(f"Query result count: {count}")
        assert isinstance(count, int)
    driver.close()