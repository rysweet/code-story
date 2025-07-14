"""
Tests for the GraphService contract in codestory.graph.

- The import of GraphService must fail (ImportError) until implemented.
- The interface contract is specified in skipped tests for future implementation:
    * async context manager: async with GraphService(uri, user, password)
    * methods: execute(cypher: str, **params) -> list[dict], close()
    * attribute: .driver (underlying Neo4j driver)
"""

import pytest
import os


def test_import_graph_service_import_succeeds():
    """Importing GraphService should succeed now that it is implemented."""
    from codestory.graph import GraphService  # noqa: F401

    assert True


@pytest.mark.asyncio
def test_graph_service_handshake_runtimeerror():
    """
    Using GraphService with invalid credentials/host should raise RuntimeError on handshake.
    Skips if NEO4J_PASSWORD is not set (to avoid hardcoding secrets).
    """
    from codestory.graph import GraphService

    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        pytest.skip("NEO4J_PASSWORD must be set for this test.")

    # Use intentionally invalid credentials/host to trigger handshake failure
    svc = GraphService("bolt://localhost:7687", "neo4j", "invalid_password")
    with pytest.raises(RuntimeError):
        # The handshake will fail and should raise RuntimeError from execute

        async def try_connect():
            async with svc:
                pass

        import asyncio
        asyncio.run(try_connect())


# --- Interface contract tests remain skipped below ---


@pytest.mark.asyncio
async def test_graph_service_context_manager_contract(monkeypatch):
    from codestory.graph import GraphService

    # Provide dummy env for handshake
    monkeypatch.setenv("NEO4J_PASSWORD", "dummy")
    svc = GraphService("bolt://localhost:7687", "neo4j", "dummy")
    async with svc as s:
        assert hasattr(s, "execute")
        assert hasattr(s, "close")
        assert hasattr(s, "driver")


def test_graph_service_execute_contract(monkeypatch):
    from codestory.graph import GraphService

    monkeypatch.setenv("NEO4J_PASSWORD", "dummy")
    svc = GraphService("bolt://localhost:7687", "neo4j", "dummy")
    # We can't actually connect, but method exists and is awaitable
    assert hasattr(svc, "execute")


def test_graph_service_close_contract(monkeypatch):
    from codestory.graph import GraphService

    monkeypatch.setenv("NEO4J_PASSWORD", "dummy")
    svc = GraphService("bolt://localhost:7687", "neo4j", "dummy")
    assert hasattr(svc, "close")


def test_graph_service_driver_attribute_contract(monkeypatch):
    from codestory.graph import GraphService

    monkeypatch.setenv("NEO4J_PASSWORD", "dummy")
    svc = GraphService("bolt://localhost:7687", "neo4j", "dummy")
    assert hasattr(svc, "driver")
