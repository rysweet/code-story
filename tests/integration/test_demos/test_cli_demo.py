from typing import Any

"""Test the CLI demo functionality."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Mark all tests with demo marker for selective running
pytestmark = pytest.mark.demo


@pytest.fixture
def setup_test_env(request: Any) -> None:
    """Set up test environment for CLI demo."""
    # Get worker ID for parallel execution to avoid conflicts
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")
    
    # Create a unique temporary test directory for each worker
    test_dir = Path(f"./demo_test_cli_{worker_id}").absolute()
    
    # Store original directory to return to after test
    original_dir = os.getcwd()
    
    try:
        # Create the test directory
        test_dir.mkdir(exist_ok=True)

        # Set environment variables for testing
        os.environ["NEO4J_URI"] = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        os.environ["NEO4J_USERNAME"] = "neo4j"
        os.environ["NEO4J_PASSWORD"] = "password"
        os.environ["NEO4J_DATABASE"] = "neo4j"
        os.environ["CODESTORY_TEST_ENV"] = "true"

        # Change to test directory
        os.chdir(test_dir)

        yield test_dir

    finally:
        # Always restore original directory first
        try:
            os.chdir(original_dir)
        except OSError:
            # If original directory doesn't exist, go to a safe location
            os.chdir(Path.home())

        # Remove test directory if it exists
        if test_dir.exists():
            import shutil
            try:
                shutil.rmtree(test_dir)
            except OSError as e:
                # Log the error but don't fail the test
                print(f"Warning: Could not remove test directory {test_dir}: {e}")


@pytest.mark.integration
def test_cli_version(setup_test_env: Any) -> None:
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
def test_cli_config_init(setup_test_env: Any) -> None:
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
def test_cli_config_show(setup_test_env: Any) -> None:
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
def test_cli_query_run(setup_test_env: Any, neo4j_connector: Any) -> None:
    """Test the CLI query run command.

    NOTE: Configuration coordination between test fixture and CLI subprocess is WORKING.
    Both processes use the same testcontainer URI (verified in logs).
    Issue is networking/timing between CLI subprocess and testcontainer.
    """
    # Xfail if testcontainer networking is not available
    import socket
    try:
        sock = socket.create_connection(("localhost", 7687), timeout=2)
        sock.close()
    except Exception:
        pytest.xfail("Neo4j testcontainer is not reachable on localhost:7687 (networking issue)")
    # Create some test data in the database
    neo4j_connector.execute_query(
        """
        CREATE (f:File {path: '/test/file.py', name: 'file.py', extension: 'py'})
        """,
        write=True,
    )

    # Get the container URI and credentials to pass to the CLI command
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.environ.get("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
    neo4j_database = os.environ.get("NEO4J_DATABASE", "neo4j")

    # Debug: Print what we're using
    print(f"DEBUG: Using Neo4j URI: {neo4j_uri}")
    print(f"DEBUG: Using Neo4j username: {neo4j_username}")
    print(f"DEBUG: Using Neo4j database: {neo4j_database}")

    # Create a runtime test config file with the exact testcontainer URIs
    import tempfile
    
    print(f"DEBUG: Creating runtime config with Neo4j URI: {neo4j_uri}")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as temp_config:
        config_content = f"""
# Runtime test configuration with testcontainer URIs
app_name = "code-story"
version = "0.1.0"
environment = "development"

[neo4j]
uri = "{neo4j_uri}"
username = "{neo4j_username}"
password = "{neo4j_password}"
database = "{neo4j_database}"

[redis]
uri = "redis://localhost:6379/0"

[openai]
api_key = "sk-test-key-openai"
embedding_model = "text-embedding-3-small"
chat_model = "gpt-4o"
reasoning_model = "gpt-4o"

[azure_openai]
api_key = "sk-test-key-azure"
endpoint = "<your-endpoint>"
deployment_id = "gpt-4o"

[service]
host = "0.0.0.0"
port = 9000

[ingestion]
config_path = "pipeline_config.yml"

[plugins]
enabled = ["filesystem"]

[telemetry]
metrics_port = 9090

[interface]
theme = "dark"

[azure]
keyvault_name = ""
"""
        temp_config.write(config_content)
        temp_config_path = temp_config.name
        
        print(f"DEBUG: Runtime config written to: {temp_config_path}")

    try:
        # Set up the environment for the subprocess to use the runtime config
        subprocess_env = os.environ.copy()
        subprocess_env.update({
            "CODESTORY_TEST_RUNTIME_CONFIG": temp_config_path,
            "CODESTORY_TEST_ENV": "true",
        })

        # First, test that the CLI can connect to the database
        print(f"DEBUG: Testing CLI connection to Neo4j...")
        connection_test = subprocess.run(
            ["codestory", "database", "status"],
            capture_output=True,
            text=True,
            check=False,
            env=subprocess_env,
        )
        print(f"DEBUG: Connection test result: {connection_test.returncode}")
        print(f"DEBUG: Connection test output: {connection_test.stdout}")
        
        # Run the query command with retry logic for testcontainer timing
        import time
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            print(f"DEBUG: Query attempt {attempt + 1}/{max_retries}")
            
            result = subprocess.run(
                ["codestory", "query", "run", "MATCH (f:File) RETURN f.path AS FilePath"],
                capture_output=True,
                text=True,
                check=False,
                env=subprocess_env,
            )

            # Debug: Print the result details
            print(f"DEBUG: CLI command return code: {result.returncode}")
            print(f"DEBUG: CLI command stdout: {result.stdout}")
            print(f"DEBUG: CLI command stderr: {result.stderr}")

            # Check if connection was successful
            if result.returncode == 0 and "Connection refused" not in result.stdout:
                break
            elif attempt < max_retries - 1:
                print(f"DEBUG: Connection failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                # Last attempt failed
                assert False, f"CLI command failed after {max_retries} attempts. STDOUT: {result.stdout}, STDERR: {result.stderr}"

        # Check that the command ran successfully
        assert result.returncode == 0, f"CLI command failed. STDOUT: {result.stdout}, STDERR: {result.stderr}"

        # Check that the output contains the test data
        assert "/test/file.py" in result.stdout

    finally:
        # Clean up the temporary config file
        try:
            os.unlink(temp_config_path)
        except OSError:
            pass


@pytest.mark.integration
def test_cli_ask(setup_test_env: Any, neo4j_connector: Any) -> None:
    """Test the CLI ask command."""
    # Xfail if OpenAI API key is not set
    import os
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("OPENAI__API_KEY"):
        pytest.xfail("OpenAI API key not set in environment")
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


@pytest.mark.integration
def test_cli_visualize(setup_test_env: Any, neo4j_connector: Any) -> None:
    """Test the CLI visualize command."""
    # Xfail if required setup is not present (e.g., Neo4j not reachable)
    import socket
    try:
        sock = socket.create_connection(("localhost", 7687), timeout=2)
        sock.close()
    except Exception:
        pytest.xfail("Neo4j testcontainer is not reachable on localhost:7687 (networking issue)")
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
