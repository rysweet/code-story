import pytest

def test_import_mcp_adapter_raises_importerror():
    """
    The MCPAdapter should not be importable until implemented.
    This test asserts that attempting to import MCPAdapter raises ImportError.
    """
    with pytest.raises(ImportError):
        from codestory.mcp import MCPAdapter  # noqa: F401

@pytest.mark.skip(reason="MCPAdapter interface contract not implemented yet")
def test_mcp_adapter_interface_contract():
    """
    Contract: MCPAdapter(graph_service: GraphService) exposes async methods:
      - searchGraph
      - summarizeNode
      - pathTo
      - similarCode
    Each method returns dict or list as per design spec.
    """
    # This test will be implemented once MCPAdapter exists.
    pass

@pytest.mark.skip(reason="MCPAdapter.searchGraph contract not implemented yet")
def test_mcp_adapter_search_graph_contract():
    """
    Contract: MCPAdapter.searchGraph returns expected dict/list shape.
    """
    pass

@pytest.mark.skip(reason="MCPAdapter.summarizeNode contract not implemented yet")
def test_mcp_adapter_summarize_node_contract():
    """
    Contract: MCPAdapter.summarizeNode returns expected dict shape.
    """
    pass

@pytest.mark.skip(reason="MCPAdapter.pathTo contract not implemented yet")
def test_mcp_adapter_path_to_contract():
    """
    Contract: MCPAdapter.pathTo returns expected list/dict shape.
    """
    pass

@pytest.mark.skip(reason="MCPAdapter.similarCode contract not implemented yet")
def test_mcp_adapter_similar_code_contract():
    """
    Contract: MCPAdapter.similarCode returns expected list/dict shape.
    """
    pass