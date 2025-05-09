"""Integration tests for the full ingestion pipeline.

These tests verify that the complete ingestion pipeline can process a
repository through all workflow steps correctly.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.llm.models import (
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    ChatMessage,
    ChatRole,
    Usage,
)
from codestory_blarify.step import BlarifyStep
from codestory_docgrapher.step import DocumentationGrapherStep
from codestory_filesystem.step import FileSystemStep
from codestory_summarizer.step import SummarizerStep

# Mark these tests as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.neo4j]


@pytest.fixture
def mock_llm_client():
    """Mock the LLM client to avoid making actual API calls during tests."""
    with patch("codestory.llm.client.create_client") as mock_create_client:
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
                        message=ChatMessage(role=ChatRole.ASSISTANT, content=response_text),
                        finish_reason="stop",
                    )
                ],
                usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            )

            return mock_response

        mock_client.chat.side_effect = mock_chat
        mock_create_client.return_value = mock_client

        yield mock_client


@pytest.fixture
def mock_docker_client():
    """Mock the Docker client for testing."""
    with patch("docker.from_env") as mock_docker:
        # Create mock container with logs method
        mock_container = MagicMock()
        mock_container.logs.return_value = (
            b"Progress: 50%\nProcessing Python files...\nProgress: 100%\nDone."
        )
        mock_container.wait.return_value = {"StatusCode": 0}

        # Create mock client
        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_client.images.pull.return_value = None
        mock_client.ping.return_value = True

        # Return mock client from from_env
        mock_docker.return_value = mock_client

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

This is a sample repository for testing the full ingestion pipeline.

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
""")

        # Create a Python file
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
def mock_steps(mock_llm_client, mock_docker_client):
    """Mock the implementation of steps to focus on pipeline integration."""
    # Mock BlarifyStep to avoid Docker dependency and improve test speed
    with patch.object(BlarifyStep, "run", autospec=True) as mock_blarify_run:
        # Mock successful job execution
        mock_blarify_run.return_value = "blarify-test-job"

        # Mock SummarizerStep to avoid dependency on graph nodes and LLM
        with patch.object(SummarizerStep, "run", autospec=True) as mock_summarizer_run:
            mock_summarizer_run.return_value = "summarizer-test-job"

            # Mock status methods to return COMPLETED
            with (
                patch.object(BlarifyStep, "status", autospec=True) as mock_blarify_status,
                patch.object(SummarizerStep, "status", autospec=True) as mock_summarizer_status,
                patch.object(
                    DocumentationGrapherStep, "status", autospec=True
                ) as mock_docgrapher_status,
            ):
                mock_blarify_status.return_value = {
                    "status": "COMPLETED",
                    "message": "Blarify step completed successfully",
                    "progress": 100.0,
                }

                mock_summarizer_status.return_value = {
                    "status": "COMPLETED",
                    "message": "Summarizer step completed successfully",
                    "progress": 100.0,
                }

                mock_docgrapher_status.return_value = {
                    "status": "COMPLETED",
                    "message": "Documentation Grapher step completed successfully",
                    "progress": 100.0,
                }

                yield


@pytest.mark.integration
def test_full_pipeline_run(sample_repo, neo4j_connector, mock_steps):
    """Test that the complete ingestion pipeline processes a repository correctly."""
    # Create the pipeline manager
    manager = PipelineManager()

    # Run the pipeline
    job_id = manager.start_job(
        repository_path=sample_repo,
        steps=["filesystem", "blarify", "summarizer", "documentation_grapher"],
        config={
            "ignore_patterns": [".git/", "__pycache__/"],
            "max_concurrency": 2,
            "use_llm": True,
        },
    )

    # Wait for the pipeline to complete (poll for status)
    max_wait_time = 120  # seconds
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        status = manager.get_job_status(job_id)
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(2)

    # Verify that the pipeline completed successfully
    assert status["status"] == "COMPLETED", f"Pipeline failed: {status.get('error')}"

    # Verify that all steps were executed
    steps_status = status.get("steps", {})
    assert "filesystem" in steps_status, "FileSystemStep was not executed"
    assert "blarify" in steps_status, "BlarifyStep was not executed"
    assert "summarizer" in steps_status, "SummarizerStep was not executed"
    assert "documentation_grapher" in steps_status, "DocumentationGrapherStep was not executed"

    # Verify that all steps completed successfully
    for step_name, step_status in steps_status.items():
        assert step_status["status"] == "COMPLETED", (
            f"Step {step_name} failed: {step_status.get('error')}"
        )

    # Verify that File nodes were created in Neo4j
    file_count = neo4j_connector.run_query(
        "MATCH (f:File) RETURN COUNT(f) as count", fetch_one=True
    )["count"]

    assert file_count >= 2, f"Expected at least 2 File nodes, got {file_count}"

    # Verify that Directory nodes were created
    dir_count = neo4j_connector.run_query(
        "MATCH (d:Directory) RETURN COUNT(d) as count", fetch_one=True
    )["count"]

    assert dir_count >= 2, f"Expected at least 2 Directory nodes, got {dir_count}"


@pytest.mark.integration
def test_pipeline_step_dependencies(sample_repo, neo4j_connector, mock_steps):
    """Test that the pipeline handles step dependencies correctly.

    This test verifies that:
    1. Dependencies are automatically resolved - when we request the summarizer step,
       the pipeline automatically runs the filesystem and blarify steps first
    2. Steps are executed in the correct order based on dependencies
    """
    # Create the pipeline manager
    manager = PipelineManager()

    # Run only the summarizer step, which depends on filesystem and blarify
    # This should run the dependencies automatically in the correct order:
    # 1. filesystem (no dependencies)
    # 2. blarify (depends on filesystem)
    # 3. summarizer (depends on filesystem and blarify)
    job_id = manager.start_job(
        repository_path=sample_repo,
        steps=["summarizer"],
        config={
            "ignore_patterns": [".git/", "__pycache__/"],
            "max_concurrency": 2,
            "use_llm": True,
        },
    )

    # Wait for the pipeline to complete (poll for status)
    max_wait_time = 120  # seconds
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        status = manager.get_job_status(job_id)
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(2)

    # Verify that the pipeline completed successfully
    assert status["status"] == "COMPLETED", f"Pipeline failed: {status.get('error')}"

    # Verify that dependent steps were executed
    steps_status = status.get("steps", {})
    assert "filesystem" in steps_status, "FileSystemStep dependency was not executed"
    assert "blarify" in steps_status, "BlarifyStep dependency was not executed"
    assert "summarizer" in steps_status, "SummarizerStep was not executed"

    # Verify the execution order based on the order in the status report
    # The status report contains steps in the order they were executed
    step_order = list(steps_status.keys())

    # Verify filesystem comes before blarify
    assert step_order.index("filesystem") < step_order.index("blarify"), (
        "FileSystemStep should execute before BlarifyStep"
    )

    # Verify blarify comes before summarizer
    assert step_order.index("blarify") < step_order.index("summarizer"), (
        "BlarifyStep should execute before SummarizerStep"
    )


@pytest.mark.integration
def test_pipeline_cancellation(sample_repo, neo4j_connector, mock_steps):
    """Test that a pipeline job can be cancelled."""
    # Modify the FileSystemStep status mock to simulate a long-running job
    with patch.object(FileSystemStep, "status", autospec=True) as mock_fs_status:
        counter = [0]

        def fs_status_side_effect(self, job_id):
            counter[0] += 1
            if counter[0] < 3:  # Return RUNNING for the first 2 calls
                return {
                    "status": "RUNNING",
                    "message": "FileSystemStep is running...",
                    "progress": 50.0,
                }
            else:  # Return COMPLETED afterwards
                return {
                    "status": "COMPLETED",
                    "message": "FileSystemStep completed successfully",
                    "progress": 100.0,
                }

        mock_fs_status.side_effect = fs_status_side_effect

        # Create the pipeline manager
        manager = PipelineManager()

        # Run the pipeline
        job_id = manager.start_job(
            repository_path=sample_repo,
            steps=["filesystem", "blarify", "summarizer"],
            config={"ignore_patterns": [".git/", "__pycache__/"]},
        )

        # Wait a moment for the job to start
        time.sleep(1)

        # Cancel the job
        cancel_result = manager.cancel_job(job_id)

        # Verify cancellation result
        assert cancel_result["status"] == "CANCELLED", "Job was not cancelled"

        # Check final job status
        status = manager.get_job_status(job_id)
        assert status["status"] == "CANCELLED", "Job status should be CANCELLED"


@pytest.mark.integration
def test_pipeline_progress_tracking(sample_repo, neo4j_connector, mock_steps):
    """Test that the pipeline tracks overall progress correctly."""
    # Modify step status mocks to simulate progress
    with (
        patch.object(FileSystemStep, "status", autospec=True) as mock_fs_status,
        patch.object(BlarifyStep, "status", autospec=True) as mock_blarify_status,
    ):
        # FileSystemStep starts at 0%, then goes to 50%, then 100%
        fs_statuses = [
            {"status": "RUNNING", "message": "Starting...", "progress": 0.0},
            {"status": "RUNNING", "message": "Processing...", "progress": 50.0},
            {"status": "COMPLETED", "message": "Done", "progress": 100.0},
        ]

        # BlarifyStep starts at 0%, then goes to 50%, then 100%
        blarify_statuses = [
            {"status": "RUNNING", "message": "Starting...", "progress": 0.0},
            {"status": "RUNNING", "message": "Processing...", "progress": 50.0},
            {"status": "COMPLETED", "message": "Done", "progress": 100.0},
        ]

        mock_fs_status.side_effect = (
            lambda self, job_id: fs_statuses.pop(0)
            if fs_statuses
            else {"status": "COMPLETED", "message": "Done", "progress": 100.0}
        )

        mock_blarify_status.side_effect = (
            lambda self, job_id: blarify_statuses.pop(0)
            if blarify_statuses
            else {"status": "COMPLETED", "message": "Done", "progress": 100.0}
        )

        # Create the pipeline manager
        manager = PipelineManager()

        # Run the pipeline with only filesystem and blarify steps
        job_id = manager.start_job(
            repository_path=sample_repo,
            steps=["filesystem", "blarify"],
            config={"ignore_patterns": [".git/", "__pycache__/"]},
        )

        # Check progress at various points
        time.sleep(0.5)
        status1 = manager.get_job_status(job_id)

        time.sleep(0.5)
        status2 = manager.get_job_status(job_id)

        time.sleep(0.5)
        status3 = manager.get_job_status(job_id)

        # Wait for the pipeline to complete
        max_wait_time = 10  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            status = manager.get_job_status(job_id)
            if status["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.5)

        final_status = manager.get_job_status(job_id)

        # Verify that progress increased over time
        assert status1.get("progress", 0) < status2.get("progress", 0), "Progress should increase"
        assert status2.get("progress", 0) < status3.get("progress", 0), "Progress should increase"
        assert final_status.get("progress", 0) == 100.0, "Final progress should be 100%"
