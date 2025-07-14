import pytest
import pytest_asyncio

from codestory.mcp import MCPAdapter


class DummyGraphService:
    def __init__(self):
        self.calls = []

    async def execute(self, cypher, **params):
        self.calls.append((cypher, params))
        # Return a stub result
        return [{"result": "ok", "cypher": cypher, "params": params}]


@pytest_asyncio.fixture
def dummy_graph_service():
    return DummyGraphService()


@pytest_asyncio.fixture
def mcp_adapter(dummy_graph_service):
    return MCPAdapter(dummy_graph_service)


@pytest.mark.asyncio
async def test_search_graph_e2e(mcp_adapter):
    cypher = "MATCH (n) RETURN n"
    params = {"foo": "bar"}
    result = await mcp_adapter.searchGraph(cypher, **params)
    assert isinstance(result, list)
    assert result and isinstance(result[0], dict)
    assert result[0]["cypher"] == cypher
    assert result[0]["params"] == params


@pytest.mark.asyncio
async def test_summarize_node_e2e(mcp_adapter):
    node_id = "abc"
    summary = await mcp_adapter.summarizeNode(node_id)
    assert isinstance(summary, str)
    assert node_id in summary


@pytest.mark.asyncio
async def test_path_to_e2e(mcp_adapter):
    src, dst = "A", "B"
    path = await mcp_adapter.pathTo(src, dst)
    assert isinstance(path, list)
    assert path[0] == src
    assert path[-1] == dst
    assert "…" in path


@pytest.mark.asyncio
async def test_similar_code_e2e(mcp_adapter):
    node_id = "abc"
    result = await mcp_adapter.similarCode(node_id)
    assert isinstance(result, list)
    assert result == []
