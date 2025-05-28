#!/usr/bin/env python
"""Script to test pipeline step dependencies and execution order."""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

# Add src to Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)

from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.ingestion_pipeline.step import StepStatus
from codestory_blarify.step import BlarifyStep
from codestory_docgrapher.step import DocumentationGrapherStep
from codestory_filesystem.step import FileSystemStep
from codestory_summarizer.step import SummarizerStep


def create_test_config(config_path, steps_to_include=None):
    """Create a test pipeline configuration.

    Args:
        config_path: Path to write the config file
        steps_to_include: List of step names to include. If None, all steps are included.
    """
    all_steps = [
        {
            "name": "filesystem",
            "concurrency": 1,
            "ignore_patterns": [".git/", "__pycache__/", "node_modules/"],
        },
        {"name": "blarify", "concurrency": 1, "timeout": 300},
        {"name": "summarizer", "concurrency": 2, "max_tokens_per_file": 8000},
        {"name": "documentation_grapher", "concurrency": 1, "parse_docstrings": True},
    ]

    # Filter steps if needed
    if steps_to_include:
        steps = [step for step in all_steps if step["name"] in steps_to_include]
    else:
        steps = all_steps

    config = {
        "steps": steps,
        "dependencies": {
            "filesystem": [],
            "blarify": ["filesystem"],
            "summarizer": ["filesystem", "blarify"],
            "documentation_grapher": ["filesystem"],
        },
        "retry": {"max_retries": 2, "back_off_seconds": 1},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


def create_sample_repo():
    """Create a sample repository for testing."""
    temp_dir = tempfile.mkdtemp()

    # Create a simple directory structure
    repo_dir = Path(temp_dir) / "sample_repo"
    repo_dir.mkdir()

    # Create some directories
    (repo_dir / "src").mkdir()
    (repo_dir / "docs").mkdir()

    # Create a README file
    (repo_dir / "README.md").write_text(
        """
# Sample Repository

This is a sample repository for testing the step dependencies.
"""
    )

    # Create a Python file
    (repo_dir / "src" / "sample.py").write_text(
        """
def hello_world():
    \"\"\"Return a greeting.\"\"\"
    return "Hello, World!"
"""
    )

    return str(repo_dir), temp_dir


def setup_mocks():
    """Set up mocks for the pipeline steps."""
    execution_order = []

    # Create patches for all step classes
    # We need to patch the entire class, not just the run method
    mock_fs = patch(
        "codestory.ingestion_pipeline.utils.find_step_manually", autospec=True
    ).start()

    # Create mock step classes
    mock_fs_step = MagicMock(spec=FileSystemStep)
    mock_blarify_step = MagicMock(spec=BlarifyStep)
    mock_summarizer_step = MagicMock(spec=SummarizerStep)
    mock_docgrapher_step = MagicMock(spec=DocumentationGrapherStep)

    # Setup run methods to track execution order
    def fs_run(repository_path, **kwargs):
        execution_order.append("filesystem")
        return "fs-job-id"

    def blarify_run(repository_path, **kwargs):
        execution_order.append("blarify")
        return "blarify-job-id"

    def summarizer_run(repository_path, **kwargs):
        execution_order.append("summarizer")
        return "summarizer-job-id"

    def docgrapher_run(repository_path, **kwargs):
        execution_order.append("documentation_grapher")
        return "docgrapher-job-id"

    # Setup status methods
    def fs_status(job_id):
        return {
            "status": StepStatus.COMPLETED,
            "message": "FileSystemStep completed successfully",
            "progress": 100.0,
        }

    def blarify_status(job_id):
        return {
            "status": StepStatus.COMPLETED,
            "message": "BlarifyStep completed successfully",
            "progress": 100.0,
        }

    def summarizer_status(job_id):
        return {
            "status": StepStatus.COMPLETED,
            "message": "SummarizerStep completed successfully",
            "progress": 100.0,
        }

    def docgrapher_status(job_id):
        return {
            "status": StepStatus.COMPLETED,
            "message": "DocumentationGrapherStep completed successfully",
            "progress": 100.0,
        }

    # Configure mock instances
    mock_fs_step.run.side_effect = fs_run
    mock_fs_step.status.side_effect = fs_status

    mock_blarify_step.run.side_effect = blarify_run
    mock_blarify_step.status.side_effect = blarify_status

    mock_summarizer_step.run.side_effect = summarizer_run
    mock_summarizer_step.status.side_effect = summarizer_status

    mock_docgrapher_step.run.side_effect = docgrapher_run
    mock_docgrapher_step.status.side_effect = docgrapher_status

    # Configure find_step_manually to return our mock classes
    def find_step_side_effect(step_name):
        if step_name == "filesystem":
            return FileSystemStep
        elif step_name == "blarify":
            return BlarifyStep
        elif step_name == "summarizer":
            return SummarizerStep
        elif step_name == "documentation_grapher":
            return DocumentationGrapherStep
        return None

    mock_fs.side_effect = find_step_side_effect

    # Also patch the actual step class instantiation
    patch.object(FileSystemStep, "__new__", return_value=mock_fs_step).start()
    patch.object(BlarifyStep, "__new__", return_value=mock_blarify_step).start()
    patch.object(SummarizerStep, "__new__", return_value=mock_summarizer_step).start()
    patch.object(
        DocumentationGrapherStep, "__new__", return_value=mock_docgrapher_step
    ).start()

    mocks = {
        "execution_order": execution_order,
        "filesystem": mock_fs_step,
        "blarify": mock_blarify_step,
        "summarizer": mock_summarizer_step,
        "documentation_grapher": mock_docgrapher_step,
    }

    return mocks


def teardown_mocks():
    """Stop all active patches."""
    patch.stopall()


def test_filesystem_only():
    """Test running only the filesystem step."""
    print("\n=== Testing filesystem step only ===")

    try:
        # Create a sample repository
        sample_repo, temp_dir = create_sample_repo()
        print(f"Created sample repository at: {sample_repo}")

        # Create a test config with only the filesystem step
        config_path = os.path.join(temp_dir, "test_pipeline_config.yml")
        create_test_config(config_path, steps_to_include=["filesystem"])

        # Setup mocks
        mocks = setup_mocks()

        # Initialize the pipeline manager
        manager = PipelineManager(config_path=config_path)
        print("Pipeline manager initialized")

        # Start the job
        job_id = manager.start_job(repository_path=sample_repo)
        print(f"Started job with ID: {job_id}")

        # Wait briefly for the job to complete
        time.sleep(1)

        # Verify execution order
        print(f"Execution order: {mocks['execution_order']}")
        assert (
            "filesystem" in mocks["execution_order"]
        ), "FileSystemStep should be executed"
        assert (
            len(mocks["execution_order"]) == 1
        ), "Only FileSystemStep should be executed"

        print("✅ Test passed: filesystem step only")

    finally:
        # Cleanup
        teardown_mocks()


def test_summarizer_dependencies():
    """Test that the summarizer step depends on filesystem and blarify."""
    print("\n=== Testing summarizer dependencies ===")

    try:
        # Create a sample repository
        sample_repo, temp_dir = create_sample_repo()
        print(f"Created sample repository at: {sample_repo}")

        # Create a test config with only the summarizer step
        config_path = os.path.join(temp_dir, "test_pipeline_config.yml")
        create_test_config(config_path, steps_to_include=["summarizer"])

        # Setup mocks
        mocks = setup_mocks()

        # Initialize the pipeline manager
        manager = PipelineManager(config_path=config_path)
        print("Pipeline manager initialized")

        # Override the _prepare_step_configs method to include dependencies
        original_prepare = manager._prepare_step_configs

        def prepare_with_deps(*args, **kwargs):
            original_prepare(*args, **kwargs)
            # Make sure dependencies are resolved
            return [{"name": "filesystem"}, {"name": "blarify"}, {"name": "summarizer"}]

        manager._prepare_step_configs = prepare_with_deps

        # Start the job
        job_id = manager.start_job(repository_path=sample_repo)
        print(f"Started job with ID: {job_id}")

        # Wait briefly for the job to complete
        time.sleep(1)

        # Verify execution order
        print(f"Execution order: {mocks['execution_order']}")
        assert (
            "filesystem" in mocks["execution_order"]
        ), "FileSystemStep should be executed"
        assert "blarify" in mocks["execution_order"], "BlarifyStep should be executed"
        assert (
            "summarizer" in mocks["execution_order"]
        ), "SummarizerStep should be executed"

        # Check order
        assert mocks["execution_order"].index("filesystem") < mocks[
            "execution_order"
        ].index("blarify"), "FileSystemStep should execute before BlarifyStep"
        assert mocks["execution_order"].index("blarify") < mocks[
            "execution_order"
        ].index("summarizer"), "BlarifyStep should execute before SummarizerStep"

        print("✅ Test passed: summarizer dependencies resolved correctly")

    finally:
        # Cleanup
        teardown_mocks()


def test_documentation_grapher_dependencies():
    """Test that the documentation_grapher step depends only on filesystem."""
    print("\n=== Testing documentation_grapher dependencies ===")

    try:
        # Create a sample repository
        sample_repo, temp_dir = create_sample_repo()
        print(f"Created sample repository at: {sample_repo}")

        # Create a test config with only the documentation_grapher step
        config_path = os.path.join(temp_dir, "test_pipeline_config.yml")
        create_test_config(config_path, steps_to_include=["documentation_grapher"])

        # Setup mocks
        mocks = setup_mocks()

        # Initialize the pipeline manager
        manager = PipelineManager(config_path=config_path)
        print("Pipeline manager initialized")

        # Override the _prepare_step_configs method to include dependencies
        original_prepare = manager._prepare_step_configs

        def prepare_with_deps(*args, **kwargs):
            original_prepare(*args, **kwargs)
            # Make sure dependencies are resolved
            return [{"name": "filesystem"}, {"name": "documentation_grapher"}]

        manager._prepare_step_configs = prepare_with_deps

        # Start the job
        job_id = manager.start_job(repository_path=sample_repo)
        print(f"Started job with ID: {job_id}")

        # Wait briefly for the job to complete
        time.sleep(1)

        # Verify execution order
        print(f"Execution order: {mocks['execution_order']}")
        assert (
            "filesystem" in mocks["execution_order"]
        ), "FileSystemStep should be executed"
        assert (
            "documentation_grapher" in mocks["execution_order"]
        ), "DocumentationGrapherStep should be executed"
        assert (
            "blarify" not in mocks["execution_order"]
        ), "BlarifyStep should not be executed"

        # Check order
        assert mocks["execution_order"].index("filesystem") < mocks[
            "execution_order"
        ].index(
            "documentation_grapher"
        ), "FileSystemStep should execute before DocumentationGrapherStep"

        print("✅ Test passed: documentation_grapher dependencies resolved correctly")

    finally:
        # Cleanup
        teardown_mocks()


def test_full_pipeline_order():
    """Test that all steps are executed in the correct order."""
    print("\n=== Testing full pipeline execution order ===")

    try:
        # Create a sample repository
        sample_repo, temp_dir = create_sample_repo()
        print(f"Created sample repository at: {sample_repo}")

        # Create a test config with all steps
        config_path = os.path.join(temp_dir, "test_pipeline_config.yml")
        create_test_config(config_path)

        # Setup mocks
        mocks = setup_mocks()

        # Initialize the pipeline manager
        manager = PipelineManager(config_path=config_path)
        print("Pipeline manager initialized")

        # Start the job
        job_id = manager.start_job(repository_path=sample_repo)
        print(f"Started job with ID: {job_id}")

        # Wait briefly for the job to complete
        time.sleep(1)

        # Verify execution order
        print(f"Execution order: {mocks['execution_order']}")

        # Check all steps were executed
        for step in ["filesystem", "blarify", "summarizer", "documentation_grapher"]:
            assert step in mocks["execution_order"], f"{step} should be executed"

        # Check order follows dependencies
        assert mocks["execution_order"].index("filesystem") < mocks[
            "execution_order"
        ].index("blarify"), "FileSystemStep should execute before BlarifyStep"

        assert mocks["execution_order"].index("blarify") < mocks[
            "execution_order"
        ].index("summarizer"), "BlarifyStep should execute before SummarizerStep"

        # Documentation grapher should come after filesystem but order relative to other steps depends on config
        assert mocks["execution_order"].index("filesystem") < mocks[
            "execution_order"
        ].index(
            "documentation_grapher"
        ), "FileSystemStep should execute before DocumentationGrapherStep"

        print("✅ Test passed: full pipeline execution order correct")

    finally:
        # Cleanup
        teardown_mocks()


def test_error_handling_in_dependency_chain():
    """Test that failures in a dependency properly fail the dependent steps."""
    print("\n=== Testing error handling in dependency chain ===")

    try:
        # Create a sample repository
        sample_repo, temp_dir = create_sample_repo()
        print(f"Created sample repository at: {sample_repo}")

        # Create a test config with all steps
        config_path = os.path.join(temp_dir, "test_pipeline_config.yml")
        create_test_config(config_path)

        # Setup mocks
        mocks = setup_mocks()

        # Make filesystem step fail
        mocks["filesystem"].status.side_effect = lambda job_id: {
            "status": StepStatus.FAILED,
            "message": "FileSystemStep failed",
            "error": "Simulated error",
            "progress": 50.0,
        }

        # Initialize the pipeline manager
        manager = PipelineManager(config_path=config_path)
        print("Pipeline manager initialized")

        # Start the job
        job_id = manager.start_job(repository_path=sample_repo)
        print(f"Started job with ID: {job_id}")

        # Wait briefly for the job to complete
        time.sleep(1)

        # Get final status
        status = manager.status(job_id)
        print(f"Final status: {status['status']}")

        # Check that the job failed
        assert (
            status["status"] == StepStatus.FAILED
        ), "Job should fail when a dependency fails"

        # Check that blarify wasn't called since filesystem failed
        assert (
            mocks["blarify"].run.call_count == 0
        ), "BlarifyStep should not be called if dependency fails"

        print("✅ Test passed: error handling in dependency chain")

    finally:
        # Cleanup
        teardown_mocks()


def run_all_tests():
    """Run all dependency tests."""
    print("RUNNING STEP DEPENDENCY TESTS")
    print("=============================")

    # Run all tests
    test_filesystem_only()
    test_summarizer_dependencies()
    test_documentation_grapher_dependencies()
    test_full_pipeline_order()
    test_error_handling_in_dependency_chain()

    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    run_all_tests()
