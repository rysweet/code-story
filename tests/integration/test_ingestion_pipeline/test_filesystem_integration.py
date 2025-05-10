"""Integration tests for the filesystem workflow step.

These tests verify that the FileSystemStep can correctly process a repository
and store its structure in the Neo4j database.
"""

import os
import tempfile
import time
from pathlib import Path

import pytest

from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import StepStatus
from codestory_filesystem.step import FileSystemStep

# Mark these tests as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.neo4j, pytest.mark.celery]


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


@pytest.fixture
def neo4j_connector():
    """Create a Neo4j connector for testing."""
    # Use direct connection parameters to connect to the test Neo4j instance
    connector = Neo4jConnector(
        uri="bolt://localhost:7688",  # Port defined in docker-compose.test.yml
        username="neo4j",
        password="password",
        database="codestory-test",  # Database defined in docker-compose.test.yml
    )

    # Clear the database before each test - this is a WRITE operation
    try:
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True, params={})
        print("Successfully connected to Neo4j and cleared the database")
    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j: {e!s}")

    yield connector

    # Close the connection
    connector.close()


# Add a custom skip condition to see the reason
# Force the test to run by removing all condition and skip decorator
@pytest.mark.integration
@pytest.mark.neo4j
@pytest.mark.celery
@pytest.mark.timeout(60)  # Limit test execution to 60 seconds
def test_filesystem_step_run(sample_repo, neo4j_connector, celery_app):
    """Test that the filesystem step can process a repository."""
    print("*** IMPORTANT: TEST IS ACTUALLY RUNNING ***")

    # Create the step
    step = FileSystemStep()
    print(f"Step created: {step}")

    # Configure Celery to run tasks eagerly (synchronously)
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    # Print configuration for debugging
    print(f"Neo4j URI: {neo4j_connector.uri}")
    print(f"Neo4j database: {neo4j_connector.database}")
    print(f"Sample repo path: {sample_repo}")
    print(f"Celery task_always_eager: {celery_app.conf.task_always_eager}")

    # Import the task
    from codestory_filesystem.step import process_filesystem

    print(f"Task imported: {process_filesystem}")
    print(f"Task registered with app? {process_filesystem.name in celery_app.tasks}")

    # Run the step
    job_id = step.run(
        repository_path=sample_repo, ignore_patterns=[".git/", "__pycache__/"]
    )
    print(f"Got job_id: {job_id}")

    # Wait for the step to complete
    max_wait_time = 30  # seconds
    start_time = time.time()
    status = None

    print(f"Waiting for job {job_id} to complete (timeout: {max_wait_time}s)...")

    while time.time() - start_time < max_wait_time:
        try:
            status = step.status(job_id)
            print(f"Job status: {status['status']} - {status.get('message', '')}")

            if status["status"] in (StepStatus.COMPLETED, StepStatus.FAILED):
                print(f"Job reached terminal state: {status['status']}")
                break
        except Exception as e:
            print(f"Error checking status: {e}")

        time.sleep(1)

    print(f"Final status: {status}")

    # Since we're using task_always_eager, the task should be completed
    assert (
        status["status"] == StepStatus.COMPLETED
    ), f"Step failed: {status.get('error')}"

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
    assert git_dir is None, ".git directory was not ignored"

    pycache_dir = neo4j_connector.execute_query(
        "MATCH (d:Directory {path: 'src/__pycache__'}) RETURN d"
    )
    assert pycache_dir is None, "__pycache__ directory was not ignored"


@pytest.mark.integration
@pytest.mark.neo4j
@pytest.mark.celery
def test_filesystem_step_ingestion_update(sample_repo, neo4j_connector, celery_app):
    """Test that the filesystem step can update an existing repository."""
    # Configure Celery to run tasks eagerly (synchronously)
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    # Create the step
    step = FileSystemStep()

    # Print configuration for debugging
    print("Running initial indexing...")

    # Run the step
    job_id = step.run(
        repository_path=sample_repo, ignore_patterns=[".git/", "__pycache__/"]
    )

    # Wait for the step to complete
    max_wait_time = 30  # seconds
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        status = step.status(job_id)
        if status["status"] == StepStatus.COMPLETED:
            break
        time.sleep(1)

    # Verify the step completed
    assert (
        status["status"] == StepStatus.COMPLETED
    ), f"Initial step failed: {status.get('error')}"

    # Check the initial file count
    file_count_query = neo4j_connector.execute_query(
        "MATCH (f:File) RETURN count(f) as count"
    )
    initial_file_count = file_count_query[0]["count"]

    # Add a new file to the repository
    print("Adding new file to repository...")
    new_file_path = Path(sample_repo) / "src" / "main" / "new_file.py"
    new_file_path.write_text("# New file")

    # Run an update
    update_job_id = step.ingestion_update(
        repository_path=sample_repo, ignore_patterns=[".git/", "__pycache__/"]
    )

    # Wait for the update to complete
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        update_status = step.status(update_job_id)
        if update_status["status"] == StepStatus.COMPLETED:
            break
        time.sleep(1)

    # Verify the update completed
    assert (
        update_status["status"] == StepStatus.COMPLETED
    ), f"Update step failed: {update_status.get('error')}"

    # Verify that the new file was added to the database
    new_file = neo4j_connector.execute_query(
        "MATCH (f:File {path: 'src/main/new_file.py'}) RETURN f", fetch_one=True
    )
    assert new_file is not None, "New file was not added to the database"

    # Verify the file count increased
    file_count_query = neo4j_connector.execute_query(
        "MATCH (f:File) RETURN count(f) as count"
    )
    updated_file_count = file_count_query[0]["count"]
    assert (
        updated_file_count > initial_file_count
    ), "File count did not increase after update"
