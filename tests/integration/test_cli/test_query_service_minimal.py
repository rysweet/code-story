import os
import pytest
import time
import requests

@pytest.mark.usefixtures("test_containers_and_service")
def test_service_cypher_query_minimal():
    # Wait for Neo4j to be ready
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable
    uri = os.environ.get("CODESTORY_NEO4J__URI") or os.environ.get("NEO4J_URI")
    username = os.environ.get("CODESTORY_NEO4J__USERNAME") or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("CODESTORY_NEO4J__PASSWORD") or os.environ.get("NEO4J_PASSWORD") or "password"
    driver = GraphDatabase.driver(uri, auth=(username, password))
    for attempt in range(30):
        try:
            with driver.session() as session:
                result = session.run("RETURN 1 AS ready")
                if result.single()["ready"] == 1:
                    print("[test_query_service_minimal] Neo4j is ready.")
                    break
        except ServiceUnavailable as e:
            print(f"[test_query_service_minimal] Waiting for Neo4j to be ready... ({e})")
            time.sleep(1)
    else:
        pytest.fail("Neo4j did not become ready in time.")
    driver.close()

    # Query the backend service's Cypher endpoint directly
    svc_port = os.environ.get("CODESTORY_TEST_PORT") or os.environ.get("PORT") or "8000"
    url = f"http://localhost:{svc_port}/v1/query/cypher"
    payload = {
        "query": "MATCH (n) RETURN count(n) as count LIMIT 5",
        "query_type": "read",
        "parameters": {},
    }
    print(f"[test_query_service_minimal] POST {url} with payload: {payload}")
    resp = requests.post(url, json=payload)
    print("Status code:", resp.status_code)
    print("Response JSON:", resp.json())
    assert resp.status_code in (200, 202)
    assert "count" in str(resp.json())