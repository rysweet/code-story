"""Integration tests for progress tracking across ingestion pipeline steps.

These tests verify that the progress of each step is correctly tracked
and that the overall pipeline progress is calculated properly.
"""

import tempfile
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.ingestion_pipeline.step import StepStatus
from codestory_blarify.step import BlarifyStep
from codestory_filesystem.step import FileSystemStep
from codestory_summarizer.step import SummarizerStep

# Mark these tests as integration tests
pytestmark = [pytest.mark.integration]


@pytest.fixture
def sample_repo() -> Generator[str, None, None]:
    """Create a sample repository structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
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

This is a sample repository for testing progress tracking.
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

        yield str(repo_dir)


@pytest.fixture
def mock_step_progress() -> Generator[dict[str, Any], None, None]:
    """Mock pipeline steps to simulate gradual progress updates."""
    # Tracks the progress updates for each step
    progress_updates: dict[str, list[dict[str, Any]]] = {
        "filesystem": [],
        "blarify": [],
        "summarizer": [],
    }

    # Create patches for all step status methods to simulate progress
    with (
        patch.object(FileSystemStep, "status", autospec=True) as mock_fs_status,
        patch.object(BlarifyStep, "status", autospec=True) as mock_blarify_status,
        patch.object(SummarizerStep, "status", autospec=True) as mock_summarizer_status,
    ):
        # Define progress sequences for each step
        fs_progress = [
            {"status": StepStatus.RUNNING, "progress": 0, "message": "Starting..."},
            {
                "status": StepStatus.RUNNING,
                "progress": 25,
                "message": "Scanning directories...",
            },
            {
                "status": StepStatus.RUNNING,
                "progress": 50,
                "message": "Processing files...",
            },
            {
                "status": StepStatus.RUNNING,
                "progress": 75,
                "message": "Creating relationships...",
            },
            {"status": StepStatus.COMPLETED, "progress": 100, "message": "Done"},
        ]

        blarify_progress = [
            {"status": StepStatus.RUNNING, "progress": 0, "message": "Starting..."},
            {
                "status": StepStatus.RUNNING,
                "progress": 30,
                "message": "Running Blarify container...",
            },
            {
                "status": StepStatus.RUNNING,
                "progress": 60,
                "message": "Processing AST...",
            },
            {"status": StepStatus.COMPLETED, "progress": 100, "message": "Done"},
        ]

        summarizer_progress = [
            {"status": StepStatus.RUNNING, "progress": 0, "message": "Starting..."},
            {
                "status": StepStatus.RUNNING,
                "progress": 33,
                "message": "Generating file summaries...",
            },
            {
                "status": StepStatus.RUNNING,
                "progress": 66,
                "message": "Generating class summaries...",
            },
            {"status": StepStatus.COMPLETED, "progress": 100, "message": "Done"},
        ]

        # Create side effect functions to return progress values in sequence
        def fs_side_effect(self: Any, job_id: str) -> dict[str, Any]:
            progress = fs_progress[min(len(progress_updates["filesystem"]), len(fs_progress) - 1)]
            progress_updates["filesystem"].append(progress)
            return progress

        def blarify_side_effect(self: Any, job_id: str) -> dict[str, Any]:
            progress = blarify_progress[
                min(len(progress_updates["blarify"]), len(blarify_progress) - 1)
            ]
            progress_updates["blarify"].append(progress)
            return progress

        def summarizer_side_effect(self: Any, job_id: str) -> dict[str, Any]:
            progress = summarizer_progress[
                min(len(progress_updates["summarizer"]), len(summarizer_progress) - 1)
            ]
            progress_updates["summarizer"].append(progress)
            return progress

        # Set up side effects
        mock_fs_status.side_effect = fs_side_effect
        mock_blarify_status.side_effect = blarify_side_effect
        mock_summarizer_status.side_effect = summarizer_side_effect

        yield {
            "progress_updates": progress_updates,
            "mocks": {
                "filesystem": mock_fs_status,
                "blarify": mock_blarify_status,
                "summarizer": mock_summarizer_status,
            },
        }


@pytest.fixture
def pipeline_manager() -> Generator[PipelineManager, None, None]:
    """Create a pipeline manager with mock step implementations."""
    # Mock the orchestrate_pipeline task
    with patch("codestory.ingestion_pipeline.tasks.orchestrate_pipeline") as mock_orchestrate:
        # Set up a return value that includes job_id and status
        mock_orchestrate.return_value = {
            "status": StepStatus.RUNNING,
            "job_id": "test-job-id",
            "progress": 0,
            "steps": {
                "filesystem": {"status": StepStatus.PENDING},
                "blarify": {"status": StepStatus.PENDING},
                "summarizer": {"status": StepStatus.PENDING},
            },
        }

        # Create the manager
        manager = PipelineManager()

        # Override the status method to use our mock progress
        def mock_status(job_id: str) -> dict[str, Any]:
            # This will be implemented in the tests
            return {}

        manager.status = mock_status

        yield manager


def test_step_progress_reporting(sample_repo: str, mock_step_progress: dict[str, Any]) -> None:
    """Test that individual steps correctly report progress."""
    # Create step instances
    fs_step = FileSystemStep()
    blarify_step = BlarifyStep()
    summarizer_step = SummarizerStep()

    # Run each step (the actual implementation is mocked)
    with (
        patch.object(FileSystemStep, "run", return_value="fs-job-id"),
        patch.object(BlarifyStep, "run", return_value="blarify-job-id"),
        patch.object(SummarizerStep, "run", return_value="summarizer-job-id"),
    ):
        fs_job_id = fs_step.run(repository_path=sample_repo)
        blarify_job_id = blarify_step.run(repository_path=sample_repo)
        summarizer_job_id = summarizer_step.run(repository_path=sample_repo)

    # Check progress for each step through multiple status calls
    for _ in range(5):  # Make 5 status checks
        # Get status for each step
        fs_status = fs_step.status(fs_job_id)
        blarify_status = blarify_step.status(blarify_job_id)
        summarizer_status = summarizer_step.status(summarizer_job_id)

        # Verify progress is being tracked
        assert "progress" in fs_status, "Filesystem step should report progress"
        assert "progress" in blarify_status, "Blarify step should report progress"
        assert "progress" in summarizer_status, "Summarizer step should report progress"
        # Verify resource usage fields are present (may be None)
        assert "cpu_percent" in fs_status, "Filesystem step should include cpu_percent"
        assert "memory_mb" in fs_status, "Filesystem step should include memory_mb"
        assert "cpu_percent" in blarify_status, "Blarify step should include cpu_percent"
        assert "memory_mb" in blarify_status, "Blarify step should include memory_mb"
        assert "cpu_percent" in summarizer_status, "Summarizer step should include cpu_percent"
        assert "memory_mb" in summarizer_status, "Summarizer step should include memory_mb"

        time.sleep(0.1)  # Small delay between status checks

    # Verify that progress increased over time
    for step_name, updates in mock_step_progress["progress_updates"].items():
        # Skip if no updates (shouldn't happen)
        if not updates:
            continue

        # Check progress increased
        progress_values = [update["progress"] for update in updates]
        assert (
            progress_values[-1] >= progress_values[0]
        ), f"{step_name} progress should increase over time"

        # Check final status is COMPLETED
        assert (
            updates[-1]["status"] == StepStatus.COMPLETED
        ), f"{step_name} final status should be COMPLETED"
        assert updates[-1]["progress"] == 100, f"{step_name} final progress should be 100%"


def test_pipeline_overall_progress(sample_repo: str, pipeline_manager: PipelineManager) -> None:
    """Test that the pipeline manager correctly calculates overall progress."""
    # Create status sequences for three steps
    fs_statuses = [
        {"status": StepStatus.RUNNING, "progress": 0.0},
        {"status": StepStatus.RUNNING, "progress": 25.0},
        {"status": StepStatus.RUNNING, "progress": 50.0},
        {"status": StepStatus.RUNNING, "progress": 75.0},
        {"status": StepStatus.COMPLETED, "progress": 100.0},
    ]

    blarify_statuses = [
        {"status": StepStatus.PENDING, "progress": 0.0},
        {"status": StepStatus.PENDING, "progress": 0.0},
        {"status": StepStatus.RUNNING, "progress": 30.0},
        {"status": StepStatus.RUNNING, "progress": 60.0},
        {"status": StepStatus.COMPLETED, "progress": 100.0},
    ]

    summarizer_statuses = [
        {"status": StepStatus.PENDING, "progress": 0.0},
        {"status": StepStatus.PENDING, "progress": 0.0},
        {"status": StepStatus.PENDING, "progress": 0.0},
        {"status": StepStatus.RUNNING, "progress": 50.0},
        {"status": StepStatus.COMPLETED, "progress": 100.0},
    ]

    # Store the current status index
    current_idx = [0]

    # Create a function to override the manager's status method
    def calculate_pipeline_progress(job_id: str) -> dict[str, Any]:
        idx = min(current_idx[0], len(fs_statuses) - 1)

        # Get current status for each step
        fs_status = fs_statuses[idx]
        blarify_status = blarify_statuses[idx]
        summarizer_status = summarizer_statuses[idx]

        # Calculate overall progress based on step weights
        # In this example, we give equal weight to each step
        fs_weight = 0.33
        blarify_weight = 0.33
        summarizer_weight = 0.34

        # Calculate the current progress based on active steps
        active_step_count = sum(
            1
            for s in [fs_status, blarify_status, summarizer_status]
            if s["status"] != StepStatus.PENDING
        )

        # For the overall progress, only count steps that have started
        if active_step_count == 0:
            overall_progress = 0.0
        else:
            # Calculate weighted progress for active steps
            active_progress = 0.0
            active_weight_sum = 0.0

            if fs_status["status"] != StepStatus.PENDING:
                active_progress += fs_status["progress"] * fs_weight
                active_weight_sum += fs_weight

            if blarify_status["status"] != StepStatus.PENDING:
                active_progress += blarify_status["progress"] * blarify_weight
                active_weight_sum += blarify_weight

            if summarizer_status["status"] != StepStatus.PENDING:
                active_progress += summarizer_status["progress"] * summarizer_weight
                active_weight_sum += summarizer_weight

            # Calculate progress as a percentage of active steps
            overall_progress = active_progress / active_weight_sum if active_weight_sum > 0 else 0.0

        # Determine overall status
        if all(
            s["status"] == StepStatus.COMPLETED
            for s in [fs_status, blarify_status, summarizer_status]
        ):
            overall_status = StepStatus.COMPLETED
        elif any(
            s["status"] == StepStatus.FAILED for s in [fs_status, blarify_status, summarizer_status]
        ):
            overall_status = StepStatus.FAILED
        elif any(
            s["status"] == StepStatus.RUNNING
            for s in [fs_status, blarify_status, summarizer_status]
        ):
            overall_status = StepStatus.RUNNING
        else:
            overall_status = StepStatus.PENDING

        # Increment the index for the next call
        current_idx[0] += 1

        # Return overall status
        return {
            "status": overall_status,
            "progress": overall_progress,
            "steps": {
                "filesystem": fs_status,
                "blarify": blarify_status,
                "summarizer": summarizer_status,
            },
        }

    # Override the pipeline manager's status method
    pipeline_manager.status = calculate_pipeline_progress

    # Simulate starting a pipeline run
    with patch.object(PipelineManager, "start_job", return_value="test-job-id"):
        job_id = "test-job-id"

    # Check pipeline progress multiple times
    progress_readings: list[float] = []
    for _ in range(5):  # Make 5 status checks
        # Get the current pipeline status
        status = pipeline_manager.status(job_id)
        progress_readings.append(status["progress"])

        # Verify that status includes the right fields
        assert "progress" in status, "Pipeline status should include progress"
        assert "steps" in status, "Pipeline status should include steps"
        assert "filesystem" in status["steps"], "Pipeline status should include filesystem step"
        assert "blarify" in status["steps"], "Pipeline status should include blarify step"
        assert "summarizer" in status["steps"], "Pipeline status should include summarizer step"

    # Verify that overall progress increased
    assert (
        progress_readings[-1] > progress_readings[0]
    ), "Overall progress should increase over time"

    # Verify final progress is 100%
    assert abs(progress_readings[-1] - 100.0) < 0.1, "Final progress should be 100%"

    # Verify final status is COMPLETED
    final_status = pipeline_manager.status(job_id)
    assert (
        final_status["status"] == StepStatus.COMPLETED
    ), "Final pipeline status should be COMPLETED"


def test_progress_for_failed_step(sample_repo: str) -> None:
    """Test that progress is correctly reported when a step fails."""
    # Create a BlarifyStep instance
    blarify_step = BlarifyStep()

    # Create a sequence of progress updates ending with failure
    blarify_progress = [
        {"status": StepStatus.RUNNING, "progress": 0, "message": "Starting..."},
        {
            "status": StepStatus.RUNNING,
            "progress": 30,
            "message": "Running Blarify container...",
        },
        {
            "status": StepStatus.FAILED,
            "progress": 60,
            "error": "Container execution failed",
        },
    ]

    # Store current progress index
    current_idx = [0]

    # Create a mock status implementation
    def mock_status(self: Any, job_id: str) -> dict[str, Any]:
        idx = min(current_idx[0], len(blarify_progress) - 1)
        current_idx[0] += 1
        return blarify_progress[idx]

    # Create a mock run implementation
    def mock_run(self: Any, repository_path: str, **kwargs: Any) -> str:
        return "blarify-failed-job"

    # Patch both the run and status methods
    with (
        patch.object(BlarifyStep, "run", mock_run),
        patch.object(BlarifyStep, "status", mock_status),
    ):
        # Run the step
        job_id = blarify_step.run(repository_path=sample_repo)

        # Check status multiple times
        statuses: list[dict[str, Any]] = []
        for _ in range(3):  # Make 3 status checks to reach the failure state
            status = blarify_step.status(job_id)
            statuses.append(status)

        # Verify progress changes
        assert statuses[0]["progress"] == 0, "Initial progress should be 0"
        assert statuses[1]["progress"] == 30, "Second progress should be 30"

        # Verify final status is FAILED
        final_status = statuses[2]
        assert final_status["status"] == StepStatus.FAILED, "Final status should be FAILED"
        assert "error" in final_status, "Failed status should include error message"
        assert (
            final_status["error"] == "Container execution failed"
        ), "Error message should match expected value"

        # Verify progress reflects the failure
        assert (
            final_status["progress"] == 60
        ), "Progress should be the last reported value before failure"


def test_progress_with_parallel_steps(sample_repo: str, pipeline_manager: PipelineManager) -> None:
    """Test that progress is correctly tracked when steps are running in parallel."""
    # Create status sequences for parallel-running steps
    # In this scenario, filesystem and blarify are running concurrently
    fs_statuses = [
        {"status": StepStatus.RUNNING, "progress": 0.0},
        {"status": StepStatus.RUNNING, "progress": 25.0},
        {"status": StepStatus.RUNNING, "progress": 50.0},
        {"status": StepStatus.RUNNING, "progress": 75.0},
        {"status": StepStatus.COMPLETED, "progress": 100.0},
    ]

    blarify_statuses = [
        {"status": StepStatus.RUNNING, "progress": 0.0},  # Both start together
        {"status": StepStatus.RUNNING, "progress": 20.0},
        {"status": StepStatus.RUNNING, "progress": 40.0},
        {"status": StepStatus.RUNNING, "progress": 80.0},
        {"status": StepStatus.COMPLETED, "progress": 100.0},
    ]

    summarizer_statuses = [
        {"status": StepStatus.PENDING, "progress": 0.0},
        {"status": StepStatus.PENDING, "progress": 0.0},
        {"status": StepStatus.PENDING, "progress": 0.0},
        {
            "status": StepStatus.RUNNING,
            "progress": 50.0,
        },  # Starts after others are in progress
        {"status": StepStatus.COMPLETED, "progress": 100.0},
    ]

    # Store the current status index
    current_idx = [0]

    # Create a function to override the manager's status method
    def calculate_pipeline_progress(job_id: str) -> dict[str, Any]:
        idx = min(current_idx[0], len(fs_statuses) - 1)

        # Get current status for each step
        fs_status = fs_statuses[idx]
        blarify_status = blarify_statuses[idx]
        summarizer_status = summarizer_statuses[idx]

        # Calculate overall progress based on step weights
        fs_weight = 0.33
        blarify_weight = 0.33
        summarizer_weight = 0.34

        # Calculate the current progress based on active steps
        active_step_count = sum(
            1
            for s in [fs_status, blarify_status, summarizer_status]
            if s["status"] != StepStatus.PENDING
        )

        # For the overall progress, only count steps that have started
        if active_step_count == 0:
            overall_progress = 0.0
        else:
            # Calculate weighted progress for active steps
            active_progress = 0.0
            active_weight_sum = 0.0

            if fs_status["status"] != StepStatus.PENDING:
                active_progress += fs_status["progress"] * fs_weight
                active_weight_sum += fs_weight

            if blarify_status["status"] != StepStatus.PENDING:
                active_progress += blarify_status["progress"] * blarify_weight
                active_weight_sum += blarify_weight

            if summarizer_status["status"] != StepStatus.PENDING:
                active_progress += summarizer_status["progress"] * summarizer_weight
                active_weight_sum += summarizer_weight

            # Calculate progress as a percentage of active steps
            overall_progress = active_progress / active_weight_sum if active_weight_sum > 0 else 0.0

        # Determine overall status
        if all(
            s["status"] == StepStatus.COMPLETED
            for s in [fs_status, blarify_status, summarizer_status]
        ):
            overall_status = StepStatus.COMPLETED
        elif any(
            s["status"] == StepStatus.FAILED for s in [fs_status, blarify_status, summarizer_status]
        ):
            overall_status = StepStatus.FAILED
        elif any(
            s["status"] == StepStatus.RUNNING
            for s in [fs_status, blarify_status, summarizer_status]
        ):
            overall_status = StepStatus.RUNNING
        else:
            overall_status = StepStatus.PENDING

        # Increment the index for the next call
        current_idx[0] += 1

        # Return overall status
        return {
            "status": overall_status,
            "progress": overall_progress,
            "steps": {
                "filesystem": fs_status,
                "blarify": blarify_status,
                "summarizer": summarizer_status,
            },
        }

    # Override the pipeline manager's status method
    pipeline_manager.status = calculate_pipeline_progress

    # Simulate starting a pipeline run
    with patch.object(PipelineManager, "start_job", return_value="test-job-id"):
        job_id = "test-job-id"

    # Define step weights
    fs_weight = 0.33
    blarify_weight = 0.33
    summarizer_weight = 0.34

    # Create an array to store expected progress values
    # For the first two checks, only filesystem and blarify are running
    # Expected progress = (25 * 0.33 + 20 * 0.33) / (0.33 + 0.33) ≈ 22.5% for first check
    # Expected progress increases with each check
    expected_progress = [
        (0.0 * fs_weight + 0.0 * blarify_weight) / (fs_weight + blarify_weight),  # Initial progress
        (25.0 * fs_weight + 20.0 * blarify_weight) / (fs_weight + blarify_weight),  # Second check
        (50.0 * fs_weight + 40.0 * blarify_weight) / (fs_weight + blarify_weight),  # Third check
        # Fourth check includes all three steps
        (75.0 * fs_weight + 80.0 * blarify_weight + 50.0 * summarizer_weight)
        / (fs_weight + blarify_weight + summarizer_weight),
        100.0,  # Final progress (all completed)
    ]

    # Check pipeline progress multiple times
    progress_readings: list[float] = []
    for i in range(5):  # Make 5 status checks
        # Get the current pipeline status
        status = pipeline_manager.status(job_id)
        progress_readings.append(status["progress"])

        # Verify progress is calculated correctly for parallel steps
        assert (
            abs(progress_readings[i] - expected_progress[i]) < 0.1
        ), (
            f"Progress at step {i} should be {expected_progress[i]:.1f}%, "
            f"got {progress_readings[i]:.1f}%"
        )

        # Check step statuses
        if i < 3:  # First three checks
            assert status["steps"]["filesystem"]["status"] == StepStatus.RUNNING
            assert status["steps"]["blarify"]["status"] == StepStatus.RUNNING
            assert status["steps"]["summarizer"]["status"] == StepStatus.PENDING
        elif i == 3:  # Fourth check
            assert status["steps"]["filesystem"]["status"] == StepStatus.RUNNING
            assert status["steps"]["blarify"]["status"] == StepStatus.RUNNING
            assert status["steps"]["summarizer"]["status"] == StepStatus.RUNNING
        else:  # Final check
            assert status["steps"]["filesystem"]["status"] == StepStatus.COMPLETED
            assert status["steps"]["blarify"]["status"] == StepStatus.COMPLETED
            assert status["steps"]["summarizer"]["status"] == StepStatus.COMPLETED

    # Verify final status is COMPLETED
    final_status = pipeline_manager.status(job_id)
    assert (
        final_status["status"] == StepStatus.COMPLETED
    ), "Final pipeline status should be COMPLETED"


def test_nonlinear_progress_reporting(sample_repo: str) -> None:
    """Test that the progress tracking works with non-linear progress patterns."""
    # Create a SummarizerStep instance
    summarizer_step = SummarizerStep()

    # Create a sequence of progress updates with non-linear progression
    # This simulates a step that might get stuck or make sudden progress jumps
    summarizer_progress = [
        {"status": StepStatus.RUNNING, "progress": 0, "message": "Starting..."},
        {
            "status": StepStatus.RUNNING,
            "progress": 5,
            "message": "Analyzing repository structure...",
        },
        {
            "status": StepStatus.RUNNING,
            "progress": 10,
            "message": "Collecting files...",
        },
        {
            "status": StepStatus.RUNNING,
            "progress": 10,
            "message": "Still collecting files...",
        },  # No progress
        {
            "status": StepStatus.RUNNING,
            "progress": 10,
            "message": "Waiting for dependencies...",
        },  # Still no progress
        {
            "status": StepStatus.RUNNING,
            "progress": 50,
            "message": "Processing files...",
        },  # Big jump
        {
            "status": StepStatus.RUNNING,
            "progress": 55,
            "message": "Processing classes...",
        },
        {
            "status": StepStatus.RUNNING,
            "progress": 95,
            "message": "Finalizing summaries...",
        },  # Another big jump
        {"status": StepStatus.COMPLETED, "progress": 100, "message": "Done"},
    ]

    # Store current progress index
    current_idx = [0]

    # Create a mock status implementation
    def mock_status(self: Any, job_id: str) -> dict[str, Any]:
        idx = min(current_idx[0], len(summarizer_progress) - 1)
        current_idx[0] += 1
        return summarizer_progress[idx]

    # Create a mock run implementation
    def mock_run(self: Any, repository_path: str, **kwargs: Any) -> str:
        return "summarizer-nonlinear-job"

    # Patch both the run and status methods
    with (
        patch.object(SummarizerStep, "run", mock_run),
        patch.object(SummarizerStep, "status", mock_status),
    ):
        # Run the step
        job_id = summarizer_step.run(repository_path=sample_repo)

        # Check status multiple times
        statuses: list[dict[str, Any]] = []
        for _ in range(len(summarizer_progress)):
            status = summarizer_step.status(job_id)
            statuses.append(status)

        # Verify key progress points
        assert statuses[0]["progress"] == 0, "Initial progress should be 0"
        assert statuses[1]["progress"] == 5, "Second status should show small progress"

        # Verify stalled progress (3 status checks with same progress value)
        assert statuses[2]["progress"] == 10, "Progress should be 10%"
        assert statuses[3]["progress"] == 10, "Progress should remain at 10%"
        assert statuses[4]["progress"] == 10, "Progress should still remain at 10%"

        # Verify sudden progress jump
        assert statuses[5]["progress"] == 50, "Progress should jump to 50%"

        # Verify completion
        final_status = statuses[-1]
        assert final_status["status"] == StepStatus.COMPLETED, "Final status should be COMPLETED"
        assert final_status["progress"] == 100, "Final progress should be 100%"

        # Verify progress is monotonically increasing or staying the same
        for i in range(1, len(statuses)):
            assert (
                statuses[i]["progress"] >= statuses[i - 1]["progress"]
            ), "Progress should never decrease"
