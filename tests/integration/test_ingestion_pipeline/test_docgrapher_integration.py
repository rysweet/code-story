"""Integration tests for the Documentation Grapher workflow step.

These tests verify that the DocumentationGrapherStep can correctly process
a repository, extract documentation entities, and store them in Neo4j.
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
from codestory_docgrapher.step import DocumentationGrapherStep
from codestory_filesystem.step import FileSystemStep

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
            # Generate a mock response
            response_text = "This is a generated summary of the code or documentation."
            
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
                            content=response_text
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
        (repo_dir / "docs").mkdir()
        
        # Create a README file
        (repo_dir / "README.md").write_text("""
# Sample Repository

This is a sample repository for testing the Documentation Grapher.

## Installation

```bash
pip install sample-repo
```

## Usage

```python
from sample_repo import SampleClass

sample = SampleClass("World")
print(sample.greet())
```

## API Reference

### SampleClass

A class that provides greeting functionality.

#### Methods

- `__init__(name)`: Initialize with a name.
- `greet()`: Return a greeting.

### main()

The main entry point for the application.
""")
        
        # Create a documentation file
        (repo_dir / "docs" / "api.md").write_text("""
# API Documentation

## SampleClass

`SampleClass` is the main class for the sample repository.

### Methods

#### `__init__(name)`

Initialize a new SampleClass instance.

**Parameters:**
- `name`: The name to greet.

#### `greet()`

Return a greeting string.

**Returns:**
- A string containing a greeting.

## Functions

### `main()`

The main entry point for the application.

**Returns:**
- None
""")
        
        # Create a Python file with docstrings
        (repo_dir / "src" / "sample.py").write_text("""
'''Sample module for testing.

This module provides a simple class for greeting.
'''

class SampleClass:
    '''A sample class for testing.
    
    This class demonstrates docstrings and provides greeting functionality.
    '''
    
    def __init__(self, name):
        '''Initialize with a name.
        
        Args:
            name: The name to greet.
        '''
        self.name = name
        
    def greet(self):
        '''Return a greeting.
        
        Returns:
            str: A greeting message.
        '''
        return f"Hello, {self.name}!"
        
def main():
    '''Main entry point.
    
    This function creates a SampleClass instance and prints a greeting.
    '''
    sample = SampleClass("World")
    print(sample.greet())
    
if __name__ == "__main__":
    main()
""")
        
        # Add some files that should be ignored
        (repo_dir / ".git").mkdir()
        (repo_dir / ".git" / "config").write_text("# Git config")
        
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
    
    # Find the sample.py file
    sample_file = neo4j_connector.run_query(
        "MATCH (f:File {path: 'src/sample.py'}) RETURN ID(f) as id",
        fetch_one=True
    )
    
    if sample_file:
        sample_file_id = sample_file["id"]
        
        # Add a Class node for SampleClass
        class_query = """
        CREATE (c:Class {
            name: 'SampleClass',
            qualified_name: 'src.sample.SampleClass',
            docstring: 'A sample class for testing.'
        })
        WITH c
        MATCH (f:File) WHERE ID(f) = $file_id
        CREATE (f)-[:CONTAINS]->(c)
        RETURN ID(c) as id
        """
        
        class_result = neo4j_connector.run_query(
            class_query,
            parameters={"file_id": sample_file_id},
            fetch_one=True
        )
        
        class_id = class_result["id"]
        
        # Add Method nodes for SampleClass
        method_queries = [
            """
            CREATE (m:Method {
                name: '__init__',
                qualified_name: 'src.sample.SampleClass.__init__',
                docstring: 'Initialize with a name.'
            })
            WITH m
            MATCH (c:Class) WHERE ID(c) = $class_id
            CREATE (c)-[:CONTAINS]->(m)
            """,
            """
            CREATE (m:Method {
                name: 'greet',
                qualified_name: 'src.sample.SampleClass.greet',
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
            qualified_name: 'src.sample.main',
            docstring: 'Main entry point.'
        })
        WITH f
        MATCH (file:File) WHERE ID(file) = $file_id
        CREATE (file)-[:CONTAINS]->(f)
        """
        
        neo4j_connector.run_query(
            main_query,
            parameters={"file_id": sample_file_id}
        )
    
    # Return the sample repository path
    return sample_repo


@pytest.mark.integration
def test_docgrapher_step_run(initialized_repo, neo4j_connector, mock_llm_client):
    """Test that the Documentation Grapher step can process a repository."""
    # Create the step
    step = DocumentationGrapherStep()
    
    # Run the step
    job_id = step.run(
        repository_path=initialized_repo,
        ignore_patterns=[".git/"]
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
    
    # Verify that Documentation nodes were created in Neo4j
    doc_count = neo4j_connector.run_query(
        "MATCH (d:Documentation) RETURN COUNT(d) as count",
        fetch_one=True
    )["count"]
    
    assert doc_count >= 3, f"Expected at least 3 Documentation nodes, got {doc_count}"
    
    # Verify that DocumentationEntity nodes were created
    entity_count = neo4j_connector.run_query(
        "MATCH (e:DocumentationEntity) RETURN COUNT(e) as count",
        fetch_one=True
    )["count"]
    
    assert entity_count > 0, "No DocumentationEntity nodes were created"
    
    # Verify relationships between documentation and code
    rel_count = neo4j_connector.run_query(
        """
        MATCH (e:DocumentationEntity)-[r:DESCRIBES|REFERENCES]->(:Class|:Method|:Function)
        RETURN COUNT(r) as count
        """,
        fetch_one=True
    )["count"]
    
    assert rel_count > 0, "No relationships between documentation and code were created"
    
    # Check specific documentation types
    readme_doc = neo4j_connector.run_query(
        "MATCH (d:Documentation {name: 'README.md'}) RETURN d",
        fetch_one=True
    )
    assert readme_doc is not None, "README.md documentation not found"
    
    api_doc = neo4j_connector.run_query(
        "MATCH (d:Documentation {name: 'api.md'}) RETURN d",
        fetch_one=True
    )
    assert api_doc is not None, "api.md documentation not found"
    
    # Verify that the LLM client was called (for content analysis)
    assert mock_llm_client.chat.called, "LLM client was not called for content analysis"


@pytest.mark.integration
def test_docgrapher_step_with_no_llm(initialized_repo, neo4j_connector):
    """Test that the Documentation Grapher step works without LLM analysis."""
    # Create the step
    step = DocumentationGrapherStep()
    
    # Run the step with use_llm=False
    job_id = step.run(
        repository_path=initialized_repo,
        ignore_patterns=[".git/"],
        use_llm=False
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
    
    # Verify that Documentation nodes were created in Neo4j
    doc_count = neo4j_connector.run_query(
        "MATCH (d:Documentation) RETURN COUNT(d) as count",
        fetch_one=True
    )["count"]
    
    assert doc_count >= 3, f"Expected at least 3 Documentation nodes, got {doc_count}"
    
    # Verify that DocumentationEntity nodes were created
    entity_count = neo4j_connector.run_query(
        "MATCH (e:DocumentationEntity) RETURN COUNT(e) as count",
        fetch_one=True
    )["count"]
    
    assert entity_count > 0, "No DocumentationEntity nodes were created"