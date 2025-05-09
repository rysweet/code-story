"""Integration tests for the ingestion pipeline.

These tests verify that the PipelineManager can orchestrate workflow steps
to process a repository and store the results in the Neo4j database.
"""

import os
import tempfile
import time
from pathlib import Path

import pytest

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.ingestion_pipeline.step import StepStatus

# Mark these tests as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.neo4j,
    pytest.mark.celery
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
def test_config():
    """Create a test configuration file for the pipeline."""
    config_content = """
    steps:
      - name: filesystem
        concurrency: 1
        ignore_patterns:
          - ".git/"
          - "__pycache__/"
    retry:
      max_retries: 2
      back_off_seconds: 1
    """
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(config_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.mark.integration
def test_pipeline_manager_run(sample_repo, neo4j_connector, test_config):
    """Test that the pipeline manager can run a workflow."""
    # Create the pipeline manager
    manager = PipelineManager(config_path=test_config)
    
    # Start a job
    job_id = manager.start_job(sample_repo)
    
    # Wait for the job to complete
    max_wait_time = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = manager.status(job_id)
        if status["status"] in (StepStatus.COMPLETED, StepStatus.FAILED):
            break
        time.sleep(2)
    
    # Verify that the job completed successfully
    assert status["status"] == StepStatus.COMPLETED, f"Job failed: {status.get('error')}"
    
    # Verify that the repository structure was stored in Neo4j
    # Check that a Repository node was created
    repo_node = neo4j_connector.find_node("Repository", {"name": os.path.basename(sample_repo)})
    assert repo_node is not None, "Repository node not found"
    
    # Check that File nodes were created
    files = neo4j_connector.run_query(
        "MATCH (f:File) RETURN count(f) as count",
        fetch_one=True
    )
    assert files["count"] > 0, "No file nodes were created"
    
    # Check that Directory nodes were created
    directories = neo4j_connector.run_query(
        "MATCH (d:Directory) RETURN count(d) as count",
        fetch_one=True
    )
    assert directories["count"] > 0, "No directory nodes were created"


@pytest.mark.integration
def test_pipeline_manager_stop(sample_repo, neo4j_connector, test_config):
    """Test that the pipeline manager can stop a running job."""
    # Create the pipeline manager
    manager = PipelineManager(config_path=test_config)
    
    # Start a job
    job_id = manager.start_job(sample_repo)
    
    # Stop the job immediately
    status = manager.stop(job_id)
    
    # Verify that the job was stopped
    assert status["status"] == StepStatus.STOPPED, f"Job was not stopped: {status}"
    
    # Wait a bit to make sure the job is fully stopped
    time.sleep(2)
    
    # Check the final status
    final_status = manager.status(job_id)
    assert final_status["status"] in (StepStatus.STOPPED, StepStatus.COMPLETED, StepStatus.FAILED), \
        f"Unexpected job status: {final_status}"


@pytest.mark.integration
def test_pipeline_manager_run_single_step(sample_repo, neo4j_connector, test_config):
    """Test that the pipeline manager can run a single step."""
    # Create the pipeline manager
    manager = PipelineManager(config_path=test_config)
    
    # Get the step class
    step_class = manager._get_step_class("filesystem")
    assert step_class is not None, "Filesystem step not found"
    
    # Run the step directly
    job_id = manager.run_single_step(
        repository_path=sample_repo,
        step_name="filesystem",
        ignore_patterns=[".git/", "__pycache__/"]
    )
    
    # Wait for the step to complete
    max_wait_time = 30  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = manager.status(job_id)
        if status["status"] in (StepStatus.COMPLETED, StepStatus.FAILED):
            break
        time.sleep(1)
    
    # Verify that the step completed successfully
    assert status["status"] == StepStatus.COMPLETED, f"Step failed: {status.get('error')}"
    
    # Verify that the repository structure was stored in Neo4j
    # Check that a Repository node was created
    repo_node = neo4j_connector.find_node("Repository", {"name": os.path.basename(sample_repo)})
    assert repo_node is not None, "Repository node not found"