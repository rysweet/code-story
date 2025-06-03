from typing import Any

"""Test the MCP demo functionality."""

import os
import subprocess
import time
from pathlib import Path

import pytest
import requests

# Mark all tests with demo marker for selective running
pytestmark = pytest.mark.demo


@pytest.fixture(scope="module")
def setup_mcp() -> None:
    """Start the MCP service for testing."""
    # Store original directory to return to after test
    original_dir = os.getcwd()

    # Change to the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    os.chdir(project_root)

    # Set environment variables for testing
    os.environ["NEO4J_URI"] = os.environ["NEO4J_URI"]
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    os.environ["CODESTORY_TEST_ENV"] = "true"
    os.environ["MCP_HOST"] = "localhost"
    os.environ["MCP_PORT"] = "8080"

    # Check if the MCP service is already running
    is_running = False
    try:
        response = requests.get("http://localhost:8080/ping")
        is_running = response.status_code == 200
    except Exception:
        pass

    if not is_running:
        # Start the MCP service
        mcp_process = subprocess.Popen(
            ["python", "-m", "codestory_mcp.main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for the service to start
        max_retries = 10
        retry_count = 0
        while retry_count < max_retries:
            try:
                response = requests.get("http://localhost:8080/ping")
                if response.status_code == 200:
                    break
            except Exception:
                pass

            time.sleep(2)
            retry_count += 1
    else:
        mcp_process = None

    yield

    # Clean up after test
    if mcp_process:
        mcp_process.terminate()
        mcp_process.wait()

    os.chdir(original_dir)


@pytest.mark.skip(reason="Requires MCP service setup")
@pytest.mark.mcp
def test_mcp_ping(setup_mcp: Any) -> None:
    """Test the MCP ping endpoint."""
    response = requests.get("http://localhost:8080/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.skip(reason="Requires MCP service setup")
@pytest.mark.mcp
def test_mcp_health(setup_mcp: Any) -> None:
    """Test the MCP health endpoint."""
    response = requests.get("http://localhost:8080/health")
    assert response.status_code == 200
    assert "status" in response.json()


@pytest.mark.skip(reason="Requires MCP service setup")
@pytest.mark.mcp
def test_mcp_tools_list(setup_mcp: Any) -> None:
    """Test the MCP tools list endpoint."""
    response = requests.get("http://localhost:8080/tools")
    assert response.status_code == 200

    tools = response.json()
    assert isinstance(tools, list)

    # Check that essential tools are available
    tool_names = [tool["name"] for tool in tools]
    assert "search_graph" in tool_names
    assert "path_to" in tool_names
    assert "summarize_node" in tool_names


@pytest.mark.skip(reason="Requires graph data and MCP service")
@pytest.mark.mcp
def test_mcp_search_graph(setup_mcp: Any, neo4j_connector: Any) -> None:
    """Test the MCP search_graph tool."""
    # Create some test data in the database
    neo4j_connector.execute_query(
        """
        CREATE (f:File {path: '/test/file.py', name: 'file.py', extension: 'py'})
        """,
        write=True,
    )

    # Run the search_graph tool
    response = requests.post(
        "http://localhost:8080/tools/search_graph",
        json={"query": "MATCH (f:File) RETURN f.path AS FilePath"},
    )

    assert response.status_code == 200
    result = response.json()
    assert "FilePath" in result[0]
    assert "/test/file.py" in result[0]["FilePath"]


@pytest.mark.skip(reason="Requires graph data and MCP service")
@pytest.mark.mcp
def test_mcp_path_to(setup_mcp: Any, neo4j_connector: Any) -> None:
    """Test the MCP path_to tool."""
    # Create some test data in the database
    neo4j_connector.execute_query(
        """
        CREATE (f1:File {path: '/test/file1.py', name: 'file1.py', extension: 'py', id: 'file:///test/file1.py'})
        CREATE (f2:File {path: '/test/file2.py', name: 'file2.py', extension: 'py', id: 'file:///test/file2.py'})
        CREATE (d:Directory {path: '/test', name: 'test', id: 'dir:///test'})
        CREATE (d)-[:CONTAINS]->(f1)
        CREATE (d)-[:CONTAINS]->(f2)
        """,
        write=True,
    )

    # Run the path_to tool
    response = requests.post(
        "http://localhost:8080/tools/path_to",
        json={
            "source_node_id": "file:///test/file1.py",
            "target_node_id": "file:///test/file2.py",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["paths"]) > 0


@pytest.mark.skip(reason="Requires OpenAI API key and MCP service")
@pytest.mark.mcp
def test_mcp_summarize_node(setup_mcp: Any, neo4j_connector: Any) -> None:
    """Test the MCP summarize_node tool."""
    # Create some test data in the database
    neo4j_connector.execute_query(
        """
        CREATE (f:File {
            path: '/test/file.py', 
            name: 'file.py', 
            extension: 'py', 
            id: 'file:///test/file.py',
            content: 'def hello(): print("Hello, world!")'
        })
        """,
        write=True,
    )

    # Run the summarize_node tool
    response = requests.post(
        "http://localhost:8080/tools/summarize_node",
        json={"node_id": "file:///test/file.py"},
    )

    assert response.status_code == 200
    result = response.json()
    assert "summary" in result
