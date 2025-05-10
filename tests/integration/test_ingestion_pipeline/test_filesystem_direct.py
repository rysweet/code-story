"""Integration tests for the filesystem workflow step using direct execution.

These tests verify that the FileSystemStep can correctly process a repository
and store its structure in the Neo4j database by directly executing the task.
"""

import os
import tempfile
from pathlib import Path

import pytest

from codestory.ingestion_pipeline.step import StepStatus, generate_job_id
from codestory_filesystem.step import process_filesystem


# Fixtures reused from test_filesystem_integration.py
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
        (repo_dir / "src" / "main" / "app.py").write_text(
            "def main():\n    print('Hello, world!')"
        )
        (repo_dir / "src" / "test" / "test_app.py").write_text(
            "def test_main():\n    assert True"
        )
        (repo_dir / "docs" / "index.md").write_text("# Documentation")

        # Add some files that should be ignored
        (repo_dir / ".git").mkdir()
        (repo_dir / ".git" / "config").write_text("# Git config")
        (repo_dir / "src" / "__pycache__").mkdir()
        (repo_dir / "src" / "__pycache__" / "app.cpython-310.pyc").write_text(
            "# Bytecode"
        )

        yield str(repo_dir)


@pytest.mark.integration
@pytest.mark.neo4j
def test_filesystem_direct(sample_repo, neo4j_connector):
    """Test that the filesystem task works correctly when executed directly."""
    print("*** IMPORTANT: TEST IS ACTUALLY RUNNING ***")

    # Generate a unique job ID
    job_id = generate_job_id()

    # Print configuration for debugging
    print(f"Neo4j URI: {neo4j_connector.uri}")
    print(f"Neo4j database: {neo4j_connector.database}")
    print(f"Sample repo path: {sample_repo}")

    # Execute the process_filesystem task directly
    print(f"Running process_filesystem task directly with job_id: {job_id}")
    result = process_filesystem(
        repository_path=sample_repo,
        job_id=job_id,
        ignore_patterns=[".git/", "__pycache__/"],
    )

    print(f"Task completed with result: {result}")

    # Verify the task completed successfully
    assert (
        result["status"] == StepStatus.COMPLETED
    ), f"Task failed: {result.get('error')}"
    assert "file_count" in result, "Missing file count in result"
    assert "dir_count" in result, "Missing directory count in result"
    assert result["file_count"] > 0, "No files were processed"
    assert result["dir_count"] > 0, "No directories were processed"

    # Verify that the repository structure was stored in Neo4j
    # 1. Check that a Repository node was created
    repo_query = neo4j_connector.execute_query(
        "MATCH (r:Repository {name: $name}) RETURN r",
        params={"name": os.path.basename(sample_repo)},
    )
    assert repo_query is not None, "Repository node not found"

    # 2. Check that Directory nodes were created
    directories = neo4j_connector.execute_query(
        "MATCH (d:Directory) RETURN d.path as path"
    )
    directory_paths = [record["path"] for record in directories]

    # Check for expected directories
    assert "src" in directory_paths, "src directory not found"
    assert "src/main" in directory_paths, "src/main directory not found"
    assert "src/test" in directory_paths, "src/test directory not found"
    assert "docs" in directory_paths, "docs directory not found"

    # 3. Check that File nodes were created
    files = neo4j_connector.execute_query("MATCH (f:File) RETURN f.path as path")
    file_paths = [record["path"] for record in files]

    # Check for expected files
    assert "README.md" in file_paths, "README.md file not found"
    assert "src/main/app.py" in file_paths, "src/main/app.py file not found"
    assert "src/test/test_app.py" in file_paths, "src/test/test_app.py file not found"
    assert "docs/index.md" in file_paths, "docs/index.md file not found"

    # 4. Check that ignored patterns were actually ignored
    git_dir = neo4j_connector.execute_query(
        "MATCH (d:Directory {path: '.git'}) RETURN d"
    )
    assert len(git_dir) == 0, ".git directory was not ignored"

    pycache_dir = neo4j_connector.execute_query(
        "MATCH (d:Directory {path: 'src/__pycache__'}) RETURN d"
    )
    assert len(pycache_dir) == 0, "__pycache__ directory was not ignored"


@pytest.mark.integration
@pytest.mark.neo4j
def test_filesystem_update_direct(sample_repo, neo4j_connector):
    """Test that the filesystem task can update an existing repository."""
    print("Running initial execution...")

    # Execute the initial ingestion
    job_id = generate_job_id()
    result = process_filesystem(
        repository_path=sample_repo,
        job_id=job_id,
        ignore_patterns=[".git/", "__pycache__/"],
    )

    # Verify the task completed successfully
    assert result["status"] == StepStatus.COMPLETED, "Initial task failed"

    # Get the initial file count
    file_count_query = neo4j_connector.execute_query(
        "MATCH (f:File) RETURN count(f) as count"
    )
    initial_file_count = file_count_query[0]["count"]
    print(f"Initial file count: {initial_file_count}")

    # Add a new file to the repository
    print("Adding new file to the repository...")
    new_file_path = Path(sample_repo) / "src" / "main" / "new_file.py"
    new_file_path.write_text("# New file")

    # Run the update
    update_job_id = generate_job_id()
    update_result = process_filesystem(
        repository_path=sample_repo,
        job_id=update_job_id,
        ignore_patterns=[".git/", "__pycache__/"],
    )

    # Verify the update task completed successfully
    assert update_result["status"] == StepStatus.COMPLETED, "Update task failed"

    # Verify that the new file was added to the database
    new_file = neo4j_connector.execute_query(
        "MATCH (f:File {path: 'src/main/new_file.py'}) RETURN f"
    )
    assert len(new_file) > 0, "New file was not added to the database"

    # Verify the file count increased
    file_count_query = neo4j_connector.execute_query(
        "MATCH (f:File) RETURN count(f) as count"
    )
    updated_file_count = file_count_query[0]["count"]
    print(f"Updated file count: {updated_file_count}")
    assert (
        updated_file_count > initial_file_count
    ), "File count did not increase after update"
