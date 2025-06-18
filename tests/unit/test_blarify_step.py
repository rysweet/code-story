import os
import types
import pytest
from unittest.mock import patch, MagicMock

from codestory_blarify.step import run_blarify

@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Clear DEPLOYMENT_MODE before each test
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)

def _fake_container(*args, **kwargs):
    class DummyContainer:
        def logs(self, **_):
            return [b"Progress: 100%"]
        def wait(self, **_):
            return {"StatusCode": 0}
        def id(self):
            return "dummy"
    return DummyContainer()

def _patch_docker(monkeypatch):
    # Patch docker.from_env() to return a context manager whose __enter__ returns a mock client
    fake_client = MagicMock()
    fake_client.containers.run.side_effect = lambda **kwargs: _fake_container()
    fake_client.containers.list.return_value = []
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_client
    fake_cm.__exit__.return_value = False
    monkeypatch.setattr("docker.from_env", lambda: fake_cm)
    return fake_client

def test_blarify_host_networking(monkeypatch, tmp_path):
    # Set host mode
    monkeypatch.setenv("DEPLOYMENT_MODE", "host")
    fake_client = _patch_docker(monkeypatch)

    # Patch get_settings to return a settings object with required fields
    class DummySettings:
        class Neo4j:
            uri = "bolt://neo4j:7687"
            username = "neo4j"
            password = type("P", (), {"get_secret_value": staticmethod(lambda: "pw")})()
            database = "neo4j"
        neo4j = Neo4j()
    monkeypatch.setattr("codestory_blarify.step.get_settings", lambda: DummySettings())

    # Patch time to avoid long waits
    monkeypatch.setattr("time.time", lambda: 0)

    # Patch update_state to no-op to avoid Celery backend errors
    monkeypatch.setattr(run_blarify, "update_state", lambda *a, **kw: None)

    # Use a real temporary directory for repository_path
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # Run
    result = run_blarify.run(
        repository_path=str(repo_dir),
        job_id="job1",
        ignore_patterns=[],
        docker_image="blarapp/blarify:latest",
        timeout=10,
        config={},
    )

    # Check that network_mode was set to host
    assert fake_client.containers.run.call_args
    kwargs = fake_client.containers.run.call_args.kwargs
    assert kwargs.get("network_mode") == "host"
    # Check that Neo4j connection string uses localhost
    cmd = kwargs["command"]
    assert any("localhost:7687" in str(arg) for arg in cmd)

def test_blarify_default_networking(monkeypatch, tmp_path):
    # Default mode (no DEPLOYMENT_MODE)
    fake_client = _patch_docker(monkeypatch)

    class DummySettings:
        class Neo4j:
            uri = "bolt://neo4j:7687"
            username = "neo4j"
            password = type("P", (), {"get_secret_value": staticmethod(lambda: "pw")})()
            database = "neo4j"
        neo4j = Neo4j()
    monkeypatch.setattr("codestory_blarify.step.get_settings", lambda: DummySettings())
    monkeypatch.setattr("time.time", lambda: 0)

    # Patch update_state to no-op to avoid Celery backend errors
    monkeypatch.setattr(run_blarify, "update_state", lambda *a, **kw: None)

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    result = run_blarify.run(
        repository_path=str(repo_dir),
        job_id="job2",
        ignore_patterns=[],
        docker_image="blarapp/blarify:latest",
        timeout=10,
        config={},
    )

    # Check that network_mode is not set
    assert fake_client.containers.run.call_args
    kwargs = fake_client.containers.run.call_args.kwargs
    assert "network_mode" not in kwargs
    # Check that Neo4j connection string does not force localhost (should use alt_host or host)
    cmd = kwargs["command"]
    # Accept either host.docker.internal or neo4j (not localhost)
    assert any(
        ("host.docker.internal" in str(arg) or "neo4j:7689" in str(arg) or "neo4j:7687" in str(arg))
        for arg in cmd
    )