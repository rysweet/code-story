"""Integration tests for the summarizer workflow step.

These tests verify that the SummarizerStep can correctly process a repository
and generate summaries for code elements in the Neo4j database.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.llm.models import (
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    ChatMessage,
    ChatRole,
    Usage,
)
from codestory_filesystem.step import FileSystemStep
from codestory_summarizer.step import SummarizerStep

# Mark these tests as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.neo4j
]


@pytest.fixture
def mock_llm_client():
    """Mock the LLM client to avoid making actual API calls during tests."""
    with patch('codestory.llm.client.create_client') as mock_create_client:
        # Create a mock client with a chat method that returns a predefined response
        mock_client = MagicMock()
        
        def mock_chat(messages, **kwargs):
            # Extract the node type from the messages
            node_type = "unknown"
            for msg in messages:
                if "File:" in msg.content:
                    node_type = "file"
                elif "Class:" in msg.content:
                    node_type = "class"
                elif "Function:" in msg.content or "Method:" in msg.content:
                    node_type = "function"
                elif "Directory:" in msg.content:
                    node_type = "directory"
                elif "Repository:" in msg.content:
                    node_type = "repository"
            
            # Generate a mock summary based on the node type
            summary_text = f"This is a generated summary for a {node_type}. It explains what the code does and why it exists."
            
            # Create a mock response
            mock_response = ChatCompletionResponse(
                id="mock-response-id",
                object="chat.completion",
                created=int(time.time()),
                model="gpt-4",
                choices=[
                    ChatCompletionResponseChoice(
                        index=0,
                        message=ChatMessage(
                            role=ChatRole.ASSISTANT,
                            content=summary_text
                        ),
                        finish_reason="stop"
                    )
                ],
                usage=Usage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150
                )
            )
            
            return mock_response
        
        mock_client.chat.side_effect = mock_chat
        mock_create_client.return_value = mock_client
        
        yield mock_client


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
        (repo_dir / "docs").mkdir()
        
        # Create some files
        (repo_dir / "README.md").write_text("# Sample Repository\n\nThis is a sample repository for testing.")
        
        # Create a simple Python class file
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
from main.app import SampleClass

class TestSampleClass(unittest.TestCase):
    def test_greet(self):
        sample = SampleClass("Test")
        self.assertEqual(sample.greet(), "Hello, Test!")
        
if __name__ == "__main__":
    unittest.main()
""")
        
        # Create a documentation file
        (repo_dir / "docs" / "index.md").write_text("""
# Documentation

Welcome to the documentation for the sample repository.

## Classes

- SampleClass: A class that provides greeting functionality.

## Functions

- main: The main entry point for the application.
""")
        
        # Add some files that should be ignored
        (repo_dir / ".git").mkdir()
        (repo_dir / ".git" / "config").write_text("# Git config")
        (repo_dir / "src" / "__pycache__").mkdir()
        (repo_dir / "src" / "__pycache__" / "app.cpython-310.pyc").write_text("# Bytecode")
        
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
def initialized_repo(sample_repo, neo4j_connector):
    """Initialize the repository in Neo4j using the FileSystemStep."""
    # Create the filesystem step
    step = FileSystemStep()
    
    # Run the step to populate the graph with filesystem nodes
    job_id = step.run(
        repository_path=sample_repo,
        ignore_patterns=[".git/", "__pycache__/"]
    )
    
    # Wait for the step to complete
    max_wait_time = 30  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = step.status(job_id)
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(1)
    
    # Verify that the step completed successfully
    assert status["status"] == "COMPLETED", f"FileSystemStep failed: {status.get('error')}"
    
    # Simulate AST nodes by adding some Class and Function nodes manually
    # In a real scenario, these would be created by the Blarify step
    
    # Find the app.py file
    app_file = neo4j_connector.run_query(
        "MATCH (f:File {path: 'src/main/app.py'}) RETURN ID(f) as id",
        fetch_one=True
    )
    
    if app_file:
        app_file_id = app_file["id"]
        
        # Add a Class node for SampleClass
        class_query = """
        CREATE (c:Class {
            name: 'SampleClass',
            qualified_name: 'src.main.app.SampleClass',
            docstring: 'A sample class for testing.'
        })
        WITH c
        MATCH (f:File) WHERE ID(f) = $file_id
        CREATE (f)-[:CONTAINS]->(c)
        RETURN ID(c) as id
        """
        
        class_result = neo4j_connector.run_query(
            class_query,
            parameters={"file_id": app_file_id},
            fetch_one=True
        )
        
        class_id = class_result["id"]
        
        # Add Method nodes for SampleClass
        method_queries = [
            """
            CREATE (m:Method {
                name: '__init__',
                qualified_name: 'src.main.app.SampleClass.__init__',
                docstring: 'Initialize with a name.'
            })
            WITH m
            MATCH (c:Class) WHERE ID(c) = $class_id
            CREATE (c)-[:CONTAINS]->(m)
            """,
            """
            CREATE (m:Method {
                name: 'greet',
                qualified_name: 'src.main.app.SampleClass.greet',
                docstring: 'Return a greeting.'
            })
            WITH m
            MATCH (c:Class) WHERE ID(c) = $class_id
            CREATE (c)-[:CONTAINS]->(m)
            """
        ]
        
        for query in method_queries:
            neo4j_connector.run_query(
                query,
                parameters={"class_id": class_id}
            )
        
        # Add a Function node for main
        main_query = """
        CREATE (f:Function {
            name: 'main',
            qualified_name: 'src.main.app.main',
            docstring: 'Main entry point.'
        })
        WITH f
        MATCH (file:File) WHERE ID(file) = $file_id
        CREATE (file)-[:CONTAINS]->(f)
        """
        
        neo4j_connector.run_query(
            main_query,
            parameters={"file_id": app_file_id}
        )
    
    # Return the sample repository path
    return sample_repo


@pytest.mark.integration
def test_summarizer_step_run(initialized_repo, neo4j_connector, mock_llm_client):
    """Test that the summarizer step can generate summaries for a repository."""
    # Create the step
    step = SummarizerStep()
    
    # Run the step
    job_id = step.run(
        repository_path=initialized_repo,
        max_concurrency=2  # Reduce concurrency for testing
    )
    
    # Wait for the step to complete (poll for status)
    max_wait_time = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = step.status(job_id)
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(1)
    
    # Verify that the step completed successfully
    assert status["status"] == "COMPLETED", f"Step failed: {status.get('error')}"
    
    # Verify that summaries were created in Neo4j
    # 1. Count the number of Summary nodes
    summary_count = neo4j_connector.run_query(
        "MATCH (s:Summary) RETURN COUNT(s) as count",
        fetch_one=True
    )["count"]
    
    # We should have summaries for:
    # - The repository
    # - Directories (src, src/main, src/test, docs)
    # - Files (README.md, app.py, test_app.py, index.md)
    # - Class (SampleClass)
    # - Methods (__init__, greet)
    # - Function (main)
    # That's a total of at least 12 summaries, but let's use a minimum to be safe
    assert summary_count >= 10, f"Expected at least 10 summaries, got {summary_count}"
    
    # 2. Check that file nodes have summaries
    file_summaries = neo4j_connector.run_query(
        """
        MATCH (f:File)-[:HAS_SUMMARY]->(s:Summary)
        RETURN COUNT(s) as count
        """,
        fetch_one=True
    )["count"]
    
    assert file_summaries >= 4, f"Expected summaries for at least 4 files, got {file_summaries}"
    
    # 3. Check that directory nodes have summaries
    dir_summaries = neo4j_connector.run_query(
        """
        MATCH (d:Directory)-[:HAS_SUMMARY]->(s:Summary)
        RETURN COUNT(s) as count
        """,
        fetch_one=True
    )["count"]
    
    assert dir_summaries >= 4, f"Expected summaries for at least 4 directories, got {dir_summaries}"
    
    # 4. Check that class nodes have summaries
    class_summaries = neo4j_connector.run_query(
        """
        MATCH (c:Class)-[:HAS_SUMMARY]->(s:Summary)
        RETURN COUNT(s) as count
        """,
        fetch_one=True
    )["count"]
    
    assert class_summaries >= 1, f"Expected summaries for at least 1 class, got {class_summaries}"
    
    # 5. Check that method nodes have summaries
    method_summaries = neo4j_connector.run_query(
        """
        MATCH (m:Method)-[:HAS_SUMMARY]->(s:Summary)
        RETURN COUNT(s) as count
        """,
        fetch_one=True
    )["count"]
    
    assert method_summaries >= 2, f"Expected summaries for at least 2 methods, got {method_summaries}"
    
    # 6. Check that function nodes have summaries
    function_summaries = neo4j_connector.run_query(
        """
        MATCH (f:Function)-[:HAS_SUMMARY]->(s:Summary)
        RETURN COUNT(s) as count
        """,
        fetch_one=True
    )["count"]
    
    assert function_summaries >= 1, f"Expected summaries for at least 1 function, got {function_summaries}"
    
    # 7. Check summary content
    sample_summary = neo4j_connector.run_query(
        """
        MATCH (s:Summary)
        RETURN s.text as text LIMIT 1
        """,
        fetch_one=True
    )["text"]
    
    assert "generated summary" in sample_summary.lower(), "Summary does not contain expected content"
    
    # 8. Verify that the mock LLM client was called
    assert mock_llm_client.chat.called, "Mock LLM client was not called"


@pytest.mark.integration
def test_summarizer_step_ingestion_update(initialized_repo, neo4j_connector, mock_llm_client):
    """Test that the summarizer step can update summaries for a modified repository."""
    # Create the step
    step = SummarizerStep()
    
    # Run the step initially
    job_id = step.run(
        repository_path=initialized_repo,
        max_concurrency=2  # Reduce concurrency for testing
    )
    
    # Wait for the step to complete
    max_wait_time = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = step.status(job_id)
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(1)
    
    # Verify that the step completed successfully
    assert status["status"] == "COMPLETED", f"Initial run failed: {status.get('error')}"
    
    # Record the number of summaries
    initial_summary_count = neo4j_connector.run_query(
        "MATCH (s:Summary) RETURN COUNT(s) as count",
        fetch_one=True
    )["count"]
    
    # Modify the repository by adding a new file
    new_file_path = Path(initialized_repo) / "src" / "main" / "new_module.py"
    new_file_path.write_text("""
def new_function():
    \"\"\"A new function added to test updates.\"\"\"
    return "I am new!"
""")
    
    # Update the filesystem representation first
    fs_step = FileSystemStep()
    fs_job_id = fs_step.ingestion_update(
        repository_path=initialized_repo,
        ignore_patterns=[".git/", "__pycache__/"]
    )
    
    # Wait for filesystem update to complete
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        status = fs_step.status(fs_job_id)
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(1)
    
    assert status["status"] == "COMPLETED", f"Filesystem update failed: {status.get('error')}"
    
    # Find the new file node
    new_file = neo4j_connector.find_node("File", {"path": "src/main/new_module.py"})
    assert new_file is not None, "New file was not added to the database"
    
    # Add a Function node for the new file
    new_file_id = neo4j_connector.run_query(
        "MATCH (f:File {path: 'src/main/new_module.py'}) RETURN ID(f) as id",
        fetch_one=True
    )["id"]
    
    neo4j_connector.run_query(
        """
        CREATE (f:Function {
            name: 'new_function',
            qualified_name: 'src.main.new_module.new_function',
            docstring: 'A new function added to test updates.'
        })
        WITH f
        MATCH (file:File) WHERE ID(file) = $file_id
        CREATE (file)-[:CONTAINS]->(f)
        """,
        parameters={"file_id": new_file_id}
    )
    
    # Run the summarizer update
    job_id = step.ingestion_update(
        repository_path=initialized_repo,
        max_concurrency=2  # Reduce concurrency for testing
    )
    
    # Wait for the update to complete
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        status = step.status(job_id)
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.time()
    
    # Verify that the update completed successfully
    assert status["status"] == "COMPLETED", f"Update failed: {status.get('error')}"
    
    # Verify that new summaries were created
    updated_summary_count = neo4j_connector.run_query(
        "MATCH (s:Summary) RETURN COUNT(s) as count",
        fetch_one=True
    )["count"]
    
    # We should have at least one new summary for the new file
    assert updated_summary_count > initial_summary_count, (
        f"Expected more summaries after update, but got {updated_summary_count} (was {initial_summary_count})"
    )
    
    # Check that the new file has a summary
    new_file_summary = neo4j_connector.run_query(
        """
        MATCH (f:File {path: 'src/main/new_module.py'})-[:HAS_SUMMARY]->(s:Summary)
        RETURN s.text as text
        """,
        fetch_one=True
    )
    
    assert new_file_summary is not None, "New file does not have a summary"
    assert "generated summary" in new_file_summary["text"].lower(), "Summary does not contain expected content"