"""
Tests for the GraphService contract in codestory.graph.

- The import of GraphService must fail (ImportError) until implemented.
- The interface contract is specified in skipped tests for future implementation:
    * async context manager: async with GraphService(uri, user, password)
    * methods: execute(cypher: str, **params) -> list[dict], close()
    * attribute: .driver (underlying Neo4j driver)
"""

import pytest

def test_import_graph_service_raises_importerror():
    """Importing GraphService should fail until implemented."""
    with pytest.raises(ImportError):
        from codestory.graph import GraphService  # noqa: F401

@pytest.mark.skip(reason="GraphService interface contract not yet implemented")
@pytest.mark.asyncio
async def test_graph_service_context_manager_contract():
    """
    GraphService should be an async context manager:
        async with GraphService(uri, user, password) as svc:
            ...
    """
    # Example usage (not implemented):
    # async with GraphService("bolt://localhost:7687", "neo4j", "secret") as svc:
    #     assert hasattr(svc, "execute")
    #     assert hasattr(svc, "close")
    #     assert hasattr(svc, "driver")
    pass

@pytest.mark.skip(reason="GraphService.execute contract not yet implemented")
def test_graph_service_execute_contract():
    """
    GraphService.execute should accept a Cypher string and params, returning a list of dicts.
    """
    # Example:
    # svc = GraphService("bolt://localhost:7687", "neo4j", "secret")
    # result = svc.execute("MATCH (n) RETURN n", foo="bar")
    # assert isinstance(result, list)
    # assert all(isinstance(row, dict) for row in result)
    pass

@pytest.mark.skip(reason="GraphService.close contract not yet implemented")
def test_graph_service_close_contract():
    """
    GraphService.close should close the underlying driver connection.
    """
    # Example:
    # svc = GraphService("bolt://localhost:7687", "neo4j", "secret")
    # svc.close()
    pass

@pytest.mark.skip(reason="GraphService.driver attribute contract not yet implemented")
def test_graph_service_driver_attribute_contract():
    """
    GraphService.driver should expose the underlying Neo4j driver object.
    """
    # Example:
    # svc = GraphService("bolt://localhost:7687", "neo4j", "secret")
    # assert hasattr(svc, "driver")
    pass