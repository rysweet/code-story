"""Test the CLI demo functionality."""

import os
import subprocess
from pathlib import Path

import pytest

# Mark all tests with demo marker for selective running
pytestmark = pytest.mark.demo


@pytest.fixture
def setup_test_env():
    """Set up test environment for CLI demo."""
    # Create a temporary test directory
    test_dir = Path("./demo_test_cli").absolute()
    test_dir.mkdir(exist_ok=True)
    
    # Store original directory to return to after test
    original_dir = os.getcwd()
    
    # Set environment variables for testing
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "testdb"
    os.environ["CODESTORY_TEST_ENV"] = "true"
    
    # Change to test directory
    os.chdir(test_dir)
    
    yield test_dir
    
    # Clean up after test
    os.chdir(original_dir)
    
    # Remove test directory if it exists
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)


@pytest.mark.integration
def test_cli_version(setup_test_env):
    """Test the CLI version command."""
    # Run the CLI command
    result = subprocess.run(
        ["codestory", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Check that the command ran successfully
    assert result.returncode == 0
    
    # Check that the output contains version information
    assert "Code Story CLI" in result.stdout


@pytest.mark.integration
def test_cli_config_init(setup_test_env):
    """Test the CLI config init command."""
    # Run the config init command
    result = subprocess.run(
        ["codestory", "config", "init"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Check that the command ran successfully
    assert result.returncode == 0
    
    # Check that a config file was created
    config_path = Path(".codestory.toml")
    assert config_path.exists()
    
    # Check content of config file
    with open(config_path) as f:
        content = f.read()
        assert "neo4j" in content
        assert "openai" in content


@pytest.mark.integration
def test_cli_config_show(setup_test_env):
    """Test the CLI config show command."""
    # First initialize the config
    subprocess.run(
        ["codestory", "config", "init"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Then run the config show command
    result = subprocess.run(
        ["codestory", "config", "show"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Check that the command ran successfully
    assert result.returncode == 0
    
    # Check that the output contains configuration information
    assert "neo4j" in result.stdout
    assert "openai" in result.stdout


@pytest.mark.integration
def test_cli_query_run(setup_test_env, neo4j_connector):
    """Test the CLI query run command."""
    # Create some test data in the database
    neo4j_connector.execute_query(
        """
        CREATE (f:File {path: '/test/file.py', name: 'file.py', extension: 'py'})
        """,
        write=True,
    )
    
    # Run the query command
    result = subprocess.run(
        ["codestory", "query", "run", "MATCH (f:File) RETURN f.path AS FilePath"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Check that the command ran successfully
    assert result.returncode == 0
    
    # Check that the output contains the test data
    assert "/test/file.py" in result.stdout


@pytest.mark.skip(reason="Requires OpenAI API key")
@pytest.mark.integration
def test_cli_ask(setup_test_env, neo4j_connector):
    """Test the CLI ask command."""
    # Create some test data in the database
    neo4j_connector.execute_query(
        """
        CREATE (f:File {path: '/test/file.py', name: 'file.py', extension: 'py'})
        CREATE (d:Directory {path: '/test', name: 'test'})
        CREATE (d)-[:CONTAINS]->(f)
        """,
        write=True,
    )
    
    # Run the ask command
    result = subprocess.run(
        ["codestory", "ask", "What files are in the repository?"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Check that the command ran successfully
    assert result.returncode == 0
    
    # Check that the output contains some response
    assert len(result.stdout) > 0


@pytest.mark.skip(reason="Requires full setup")
@pytest.mark.integration
def test_cli_visualize(setup_test_env, neo4j_connector):
    """Test the CLI visualize command."""
    # Create some test data in the database
    neo4j_connector.execute_query(
        """
        CREATE (f:File {path: '/test/file.py', name: 'file.py', extension: 'py'})
        CREATE (d:Directory {path: '/test', name: 'test'})
        CREATE (d)-[:CONTAINS]->(f)
        """,
        write=True,
    )
    
    # Run the visualize command
    result = subprocess.run(
        ["codestory", "visualize", "--path", "visualization.html"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Check that the command ran successfully
    assert result.returncode == 0
    
    # Check that the visualization file was created
    viz_path = Path("visualization.html")
    assert viz_path.exists()
    
    # Check content of visualization file
    with open(viz_path) as f:
        content = f.read()
        assert "html" in content
        assert "javascript" in content