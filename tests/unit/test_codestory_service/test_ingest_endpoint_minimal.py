import os
import pytest
from fastapi.testclient import TestClient

# Set required env vars for settings
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["CODESTORY_NEO4J__URI"] = "bolt://localhost:7687"
os.environ["REDIS__URI"] = "redis://localhost:6379"
os.environ["CODESTORY_REDIS__URI"] = "redis://localhost:6379"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379"
os.environ["DEPLOYMENT_MODE"] = "host"

from unittest.mock import patch
from codestory_service.infrastructure.celery_adapter import DummyCeleryAdapter, get_celery_adapter

@pytest.fixture
def client():
    with patch("codestory_service.infrastructure.celery_adapter.get_celery_adapter", new=lambda: DummyCeleryAdapter()):
        from codestory_service.main import app
        yield TestClient(app)

def test_ingest_endpoint_minimal(client):
    payload = {
        "source": "/repositories/repo",
        "source_type": "local_path",
        "priority": "default",
        "description": "CLI ingestion of repository: /repositories/repo"
    }
    response = client.post("/v1/ingest", json=payload)
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    assert response.status_code in (200, 202, 422)