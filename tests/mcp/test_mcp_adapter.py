import pytest

import pytest_asyncio

from codestory.mcp import MCPAdapter


class DummyGraphService:
    async def execute(self, cypher, **params):
        return [{"result": "ok", "cypher": cypher, "params": params}]


@pytest_asyncio.fixture
def mcp_adapter():
    return MCPAdapter(DummyGraphService())


def test_mcp_adapter_instantiation():
    adapter = MCPAdapter(DummyGraphService())
    assert isinstance(adapter, MCPAdapter)


@pytest.mark.asyncio
async def test_search_graph_returns_expected_list(mcp_adapter):
    cypher = "MATCH (n) RETURN n"
    params = {"foo": "bar"}
    result = await mcp_adapter.searchGraph(cypher, **params)
    assert isinstance(result, list)
    assert result and isinstance(result[0], dict)
    assert result[0]["cypher"] == cypher
    assert result[0]["params"] == params


@pytest.mark.asyncio
async def test_summarize_node_returns_stub(mcp_adapter):
    node_id = "123"
    summary = await mcp_adapter.summarizeNode(node_id)
    assert isinstance(summary, str)
    assert node_id in summary


@pytest.mark.asyncio
async def test_path_to_returns_stub(mcp_adapter):
    src, dst = "A", "B"
    path = await mcp_adapter.pathTo(src, dst)
    assert isinstance(path, list)
    assert path[0] == src
    assert path[-1] == dst
    assert "…" in path


@pytest.mark.asyncio
async def test_similar_code_returns_empty_list(mcp_adapter):
    node_id = "123"
    result = await mcp_adapter.similarCode(node_id)
    assert isinstance(result, list)
    assert result == []
