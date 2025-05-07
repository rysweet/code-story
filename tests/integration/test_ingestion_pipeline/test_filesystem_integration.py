"""Integration tests for the filesystem workflow step.

These tests verify that the FileSystemStep can correctly process a repository
and store its structure in the Neo4j database.
"""

import os
import tempfile
import time
import pytest
from pathlib import Path

from src.codestory.config.settings import get_settings
from src.codestory.graphdb.neo4j_connector import Neo4jConnector
from src.codestory_filesystem.step import FileSystemStep


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
        (repo_dir / "docs").mkdir()
        
        # Create some files
        (repo_dir / "README.md").write_text("# Sample Repository")
        (repo_dir / "src" / "main" / "app.py").write_text("def main():\n    print('Hello, world!')")
        (repo_dir / "src" / "test" / "test_app.py").write_text(
            "def test_main():\n    assert True"
        )
        (repo_dir / "docs" / "index.md").write_text("# Documentation")
        
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


@pytest.mark.integration
def test_filesystem_step_run(sample_repo, neo4j_connector):
    """Test that the filesystem step can process a repository."""
    # Create the step
    step = FileSystemStep()
    
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
    
    # Verify that the repository structure was stored in Neo4j
    # 1. Check that a Repository node was created
    repo_node = neo4j_connector.find_node("Repository", {"name": os.path.basename(sample_repo)})
    assert repo_node is not None, "Repository node not found"
    
    # 2. Check that Directory nodes were created
    directories = neo4j_connector.run_query(
        "MATCH (d:Directory) RETURN d.path as path",
        fetch_all=True
    )
    directory_paths = [record["path"] for record in directories]
    
    # Check for expected directories
    assert "src" in directory_paths, "src directory not found"
    assert "src/main" in directory_paths, "src/main directory not found"
    assert "src/test" in directory_paths, "src/test directory not found"
    assert "docs" in directory_paths, "docs directory not found"
    
    # 3. Check that File nodes were created
    files = neo4j_connector.run_query(
        "MATCH (f:File) RETURN f.path as path",
        fetch_all=True
    )
    file_paths = [record["path"] for record in files]
    
    # Check for expected files
    assert "README.md" in file_paths, "README.md file not found"
    assert "src/main/app.py" in file_paths, "src/main/app.py file not found"
    assert "src/test/test_app.py" in file_paths, "src/test/test_app.py file not found"
    assert "docs/index.md" in file_paths, "docs/index.md file not found"
    
    # 4. Check that ignored patterns were actually ignored
    git_dir = neo4j_connector.find_node("Directory", {"path": ".git"})
    assert git_dir is None, ".git directory was not ignored"
    
    pycache_dir = neo4j_connector.find_node("Directory", {"path": "src/__pycache__"})
    assert pycache_dir is None, "__pycache__ directory was not ignored"
    
    # 5. Check relationships between nodes
    # Repository -> Directory relationships
    repo_contains = neo4j_connector.run_query(
        """
        MATCH (r:Repository)-[:CONTAINS]->(d:Directory)
        WHERE r.name = $repo_name
        RETURN d.path as path
        """,
        parameters={"repo_name": os.path.basename(sample_repo)},
        fetch_all=True
    )
    top_level_dirs = [record["path"] for record in repo_contains]
    assert "src" in top_level_dirs, "Repository not connected to src directory"
    assert "docs" in top_level_dirs, "Repository not connected to docs directory"
    
    # Directory -> File relationships
    dir_files = neo4j_connector.run_query(
        """
        MATCH (d:Directory)-[:CONTAINS]->(f:File)
        WHERE d.path = 'src/main'
        RETURN f.path as path
        """,
        fetch_all=True
    )
    main_files = [record["path"] for record in dir_files]
    assert "src/main/app.py" in main_files, "src/main directory not connected to app.py file"


@pytest.mark.integration
def test_filesystem_step_ingestion_update(sample_repo, neo4j_connector):
    """Test that the filesystem step can update an existing repository."""
    # Create the step
    step = FileSystemStep()
    
    # Run the step
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
    assert status["status"] == "COMPLETED", f"Step failed: {status.get('error')}"
    
    # Add a new file to the repository
    new_file_path = Path(sample_repo) / "src" / "main" / "new_file.py"
    new_file_path.write_text("# New file")
    
    # Run an update (ingestion_update should be the same as run for this step)
    job_id = step.ingestion_update(
        repository_path=sample_repo,
        ignore_patterns=[".git/", "__pycache__/"]
    )
    
    # Wait for the step to complete
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = step.status(job_id)
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(1)
    
    # Verify that the step completed successfully
    assert status["status"] == "COMPLETED", f"Step failed: {status.get('error')}"
    
    # Verify that the new file was added to the database
    new_file = neo4j_connector.find_node("File", {"path": "src/main/new_file.py"})
    assert new_file is not None, "New file was not added to the database"