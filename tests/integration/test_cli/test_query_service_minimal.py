# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

from tests.conftest import get_test_config
import pytest
import time
import requests

@pytest.mark.usefixtures("unified_test_env")
def test_service_cypher_query_minimal():
    """Test minimal service Cypher endpoint using unified_test_env."""
    config = get_test_config()
    svc_port = config.get("CODESTORY_TEST_PORT") or config.get("PORT") or "8000"
    url = f"http://localhost:{svc_port}/v1/query/cypher"
    payload = {
        "query": "MATCH (n) RETURN count(n) as count LIMIT 5",
        "query_type": "read",
        "parameters": {},
    }
    resp = requests.post(url, json=payload)
    assert resp.status_code in (200, 202)
    assert "count" in str(resp.json())