import os
import pytest
from fastapi.testclient import TestClient
from codestory_service.main import app
from codestory_service.infrastructure.host_health import HostServiceHealth

@pytest.fixture(autouse=True)
def set_host_mode_env(monkeypatch):
    monkeypatch.setenv("DEPLOYMENT_MODE", "host")
    yield
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)

def test_health_endpoint_host(monkeypatch):
    # Set env and override before any import
    monkeypatch.setenv("DEPLOYMENT_MODE", "host")

    class FakeHostServiceHealth:
        def __init__(self):
            print("FakeHostServiceHealth instantiated")
        async def check_neo4j(self): return False
        async def check_redis(self): return False
        async def summary(self): return {"neo4j": False, "redis": False, "service": True}

    def fake_host_health_provider():
        return FakeHostServiceHealth()

    import sys
    if "codestory_service.main" in sys.modules:
        del sys.modules["codestory_service.main"]
    if "codestory_service.api.health" in sys.modules:
        del sys.modules["codestory_service.api.health"]

    from codestory_service.api import health as health_api
    from codestory_service.main import app
    from fastapi.testclient import TestClient

    app.dependency_overrides = {}
    app.dependency_overrides[health_api.get_host_health_provider] = lambda: FakeHostServiceHealth()

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data
    for key in ("neo4j", "redis", "service"):
        assert key in data["components"]
        assert data["components"][key]["status"] in ("healthy", "unhealthy")

    app.dependency_overrides = {}

def test_host_service_health_summary(monkeypatch):
    async def fake_check_true(self): return True
    monkeypatch.setattr(HostServiceHealth, "check_neo4j", fake_check_true)
    monkeypatch.setattr(HostServiceHealth, "check_redis", fake_check_true)
    health = HostServiceHealth()
    import asyncio
    summary = asyncio.get_event_loop().run_until_complete(health.summary())
    assert summary == {"neo4j": True, "redis": True, "service": True}