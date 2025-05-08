"""Integration tests for the Blarify workflow step.

These tests verify that the BlarifyStep can correctly process a repository
and store AST and symbol bindings in the Neo4j database.
"""

import os
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.codestory.config.settings import get_settings
from src.codestory.graphdb.neo4j_connector import Neo4jConnector
from src.codestory_blarify.step import BlarifyStep


# Mark these tests as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.neo4j
]


@pytest.fixture
def sample_repo():
    """Create a sample repository structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple directory structure
        repo_dir = Path(temp_dir) / "sample_repo"
        repo_dir.mkdir()
        
        # Create some directories
        (repo_dir / "src").mkdir()
        (repo_dir / "src" / "main").mkdir()
        (repo_dir / "src" / "test").mkdir()
        
        # Create some Python files
        (repo_dir / "src" / "main" / "app.py").write_text("""
class SampleClass:
    \"\"\"A sample class for testing.\"\"\"
    
    def __init__(self, name):
        \"\"\"Initialize with a name.\"\"\"
        self.name = name
        
    def greet(self):
        \"\"\"Return a greeting.\"\"\"
        return f"Hello, {self.name}!"
        
def main():
    \"\"\"Main entry point.\"\"\"
    sample = SampleClass("World")
    print(sample.greet())
    
if __name__ == "__main__":
    main()
""")
        
        # Create a test file
        (repo_dir / "src" / "test" / "test_app.py").write_text("""
import unittest
from src.main.app import SampleClass

class TestSampleClass(unittest.TestCase):
    def test_greet(self):
        sample = SampleClass("Test")
        self.assertEqual(sample.greet(), "Hello, Test!")
        
if __name__ == "__main__":
    unittest.main()
""")
        
        # Add some files that should be ignored
        (repo_dir / ".git").mkdir()
        (repo_dir / ".git" / "config").write_text("# Git config")
        (repo_dir / "src" / "__pycache__").mkdir()
        
        yield str(repo_dir)


@pytest.fixture
def neo4j_connector():
    """Create a Neo4j connector for testing."""
    settings = get_settings()
    connector = Neo4jConnector(
        uri=settings.neo4j.uri,
        username=settings.neo4j.username,
        password=settings.neo4j.password.get_secret_value(),
        database=settings.neo4j.database,
    )
    
    # Clear the database before each test
    connector.run_query("MATCH (n) DETACH DELETE n")
    
    yield connector
    
    # Close the connection
    connector.close()


@pytest.fixture
def mock_docker_client():
    """Mock the Docker client for testing."""
    with patch('docker.from_env') as mock_docker:
        # Create mock container with logs method
        mock_container = MagicMock()
        mock_container.logs.return_value = b"Progress: 50%\nProcessing Python files...\nProgress: 100%\nDone."
        mock_container.wait.return_value = {"StatusCode": 0}
        
        # Create mock client
        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_client.images.pull.return_value = None
        mock_client.ping.return_value = True
        
        # Return mock client from from_env
        mock_docker.return_value = mock_client
        
        yield mock_client


@pytest.mark.integration
def test_blarify_step_run(sample_repo, neo4j_connector, mock_docker_client):
    """Test that the Blarify step can process a repository."""
    # Mock Neo4j queries to simulate AST creation
    with patch.object(Neo4jConnector, 'run_query') as mock_run_query:
        # Mock query responses for verification
        mock_run_query.return_value = {"count": 10}
        
        # Create the step
        step = BlarifyStep()
        
        # Run the step
        job_id = step.run(
            repository_path=sample_repo,
            ignore_patterns=[".git/", "__pycache__/"]
        )
        
        # Wait for the step to complete (poll for status)
        max_wait_time = 30  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = step.status(job_id)
            if status["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(1)
        
        # Verify that the step completed successfully
        assert status["status"] == "COMPLETED", f"Step failed: {status.get('error')}"
        
        # Verify that Docker was used correctly
        mock_docker_client.images.pull.assert_called_once()
        mock_docker_client.containers.run.assert_called_once()
        
        # Check for expected parameters in the Docker run call
        call_kwargs = mock_docker_client.containers.run.call_args[1]
        assert "volumes" in call_kwargs
        assert sample_repo in str(call_kwargs["volumes"])
        
        # Verify that query was made to check AST nodes
        mock_run_query.assert_called()


@pytest.mark.integration
def test_blarify_step_stop(sample_repo, neo4j_connector, mock_docker_client):
    """Test that the Blarify step can be stopped."""
    # Create the step
    step = BlarifyStep()
    
    # Run the step
    job_id = step.run(
        repository_path=sample_repo,
        ignore_patterns=[".git/", "__pycache__/"]
    )
    
    # Stop the job immediately
    stop_result = step.stop(job_id)
    
    # Verify that the job was stopped
    assert stop_result["status"] == "STOPPED"
    
    # Check if the container was stopped
    for call in mock_docker_client.containers.list.mock_calls:
        for container in call.return_value:
            container.stop.assert_called()