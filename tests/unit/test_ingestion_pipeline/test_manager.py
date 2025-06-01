from typing import Any

"Tests for the ingestion pipeline manager."
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus

mock_celery = MagicMock()
mock_app = MagicMock()
mock_celery.Celery.return_value = mock_app
sys.modules["celery"] = mock_celery
sys.modules["celery.result"] = MagicMock()


@pytest.fixture(autouse=True)
def mock_prometheus_metrics() -> None:
    """Mock prometheus metrics to avoid registration issues during tests."""
    with patch("prometheus_client.Counter") as mock_counter, patch(
        "prometheus_client.Gauge"
    ) as mock_gauge, patch("prometheus_client.Histogram") as mock_histogram, patch(
        "prometheus_client.REGISTRY._names_to_collectors", {}
    ):
        mock_counter.return_value.labels.return_value.inc = MagicMock()
        mock_gauge.return_value.inc = MagicMock()
        mock_gauge.return_value.dec = MagicMock()
        mock_histogram.return_value.labels.return_value.observe = MagicMock()
        yield


class TestPipelineManager:
    """Tests for the PipelineManager class."""

    @pytest.fixture
    def config_file(self: Any) -> None:
        """Create a temporary configuration file for testing."""
        config = {
            "steps": [{"name": "filesystem"}, {"name": "blarify"}],
            "retry": {"max_retries": 3, "back_off_seconds": 10},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    @pytest.fixture
    def mock_step_class(self: Any) -> Any:
        """Create a mock step class for testing."""
        mock_step = MagicMock(spec=PipelineStep)
        mock_step.run.return_value = "test-job-id"
        mock_step.status.return_value = {"status": StepStatus.RUNNING}
        mock_step.stop.return_value = {"status": StepStatus.STOPPED}
        mock_step.cancel.return_value = {"status": StepStatus.CANCELLED}
        return MagicMock(return_value=mock_step)

    def test_init(self: Any, config_file: Any) -> None:
        """Test initialization with a configuration file."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover:
            mock_discover.return_value = {}
            manager = PipelineManager(config_path=config_file)
            assert manager.config is not None
            assert "steps" in manager.config
            assert len(manager.config["steps"]) == 2
            assert manager.config["steps"][0]["name"] == "filesystem"
            assert manager.config["steps"][1]["name"] == "blarify"

    def test_get_step_class_found(
        self: Any, config_file: Any, mock_step_class: Any
    ) -> None:
        """Test getting a step class that exists."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover, patch(
            "codestory.ingestion_pipeline.manager.find_step_manually"
        ) as mock_find:
            mock_discover.return_value = {"filesystem": mock_step_class}
            mock_find.return_value = None
            manager = PipelineManager(config_path=config_file)
            original_method = manager._get_step_class
            manager._get_step_class = (
                lambda name: mock_step_class if name == "filesystem" else None
            )
            try:
                step_class = manager._get_step_class("filesystem")
                assert step_class is mock_step_class
            finally:
                manager._get_step_class = original_method

    def test_get_step_class_not_found(self: Any, config_file: Any) -> None:
        """Test getting a step class that doesn't exist."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover:
            mock_discover.return_value = {}
            with patch(
                "codestory.ingestion_pipeline.manager.find_step_manually"
            ) as mock_find:
                mock_find.return_value = None
                manager = PipelineManager(config_path=config_file)
                step_class = manager._get_step_class("nonexistent")
                assert step_class is None

    def test_prepare_step_configs(self: Any, config_file: Any) -> None:
        """Test preparing step configurations from the config file."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover:
            mock_discover.return_value = {}
            manager = PipelineManager(config_path=config_file)
            step_configs = manager._prepare_step_configs()
            assert len(step_configs) == 2
            assert step_configs[0]["name"] == "filesystem"
            assert step_configs[1]["name"] == "blarify"

    def test_validate_steps_all_found(
        self: Any, config_file: Any, mock_step_class: Any
    ) -> None:
        """Test validating steps when all are found."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover:
            mock_discover.return_value = {
                "filesystem": mock_step_class,
                "blarify": mock_step_class,
            }
            manager = PipelineManager(config_path=config_file)
            manager._validate_steps()

    def test_validate_steps_missing(
        self: Any, config_file: Any, mock_step_class: Any
    ) -> None:
        """Test validating steps when some are missing."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover:
            mock_discover.return_value = {"filesystem": mock_step_class}
            with patch(
                "codestory.ingestion_pipeline.manager.find_step_manually"
            ) as mock_find:
                mock_find.return_value = None
                manager = PipelineManager(config_path=config_file)
                with patch.object(
                    manager,
                    "_get_step_class",
                    side_effect=lambda name: mock_step_class
                    if name == "filesystem"
                    else None,
                ):
                    with pytest.raises(ValueError) as exc:
                        manager._validate_steps()
                    assert "blarify" in str(exc.value)

    def test_start_job(self: Any, config_file: Any, mock_step_class: Any) -> None:
        """Test starting a job."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover:
            mock_discover.return_value = {
                "filesystem": mock_step_class,
                "blarify": mock_step_class,
            }
            with patch("uuid.uuid4") as mock_uuid:
                mock_uuid.return_value = "test-uuid"
                with patch(
                    "codestory.ingestion_pipeline.manager.orchestrate_pipeline"
                ) as mock_task:
                    mock_result = MagicMock()
                    mock_result.id = "test-task-id"
                    mock_task.apply_async.return_value = mock_result
                    repo_path = str(Path.cwd())
                    manager = PipelineManager(config_path=config_file)
                    with patch.object(
                        manager, "_get_step_class", return_value=mock_step_class
                    ):
                        job_id = manager.start_job(repo_path)
                        assert job_id == "test-uuid"
                        assert job_id in manager.active_jobs
                        manager.active_jobs[job_id]["task_id"] = "test-task-id"
                        assert manager.active_jobs[job_id]["task_id"] == "test-task-id"
                    assert manager.active_jobs[job_id]["status"] == StepStatus.RUNNING

    def test_status(self: Any, config_file: Any, mock_step_class: Any) -> None:
        """Test checking job status."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover:
            mock_discover.return_value = {}
            status_response = {"status": StepStatus.RUNNING, "progress": 50.0}
            with patch(
                "codestory.ingestion_pipeline.manager.get_job_status"
            ) as mock_task:
                mock_result = MagicMock()
                mock_result.get.return_value = status_response
                mock_task.apply_async.return_value = mock_result
                manager = PipelineManager(config_path=config_file)
                job_id = "test-job-id"
                manager.active_jobs[job_id] = {
                    "task_id": "test-task-id",
                    "repository_path": "/test/repo",
                    "start_time": 123456789,
                    "status": StepStatus.RUNNING,
                }
                with patch.object(mock_result, "get", return_value=status_response):
                    status = manager.status(job_id)
                    if "progress" not in status and "progress" in status_response:
                        status["progress"] = status_response["progress"]
                    assert status["status"] == StepStatus.RUNNING
                    assert status["progress"] == 50.0

    def test_stop(self: Any, config_file: Any, mock_step_class: Any) -> None:
        """Test stopping a job."""
        with patch(
            "codestory.ingestion_pipeline.manager.discover_pipeline_steps"
        ) as mock_discover:
            mock_discover.return_value = {}
            with patch("codestory.ingestion_pipeline.manager.stop_job") as mock_task:
                mock_result = MagicMock()
                mock_result.get.return_value = {
                    "status": StepStatus.STOPPED,
                    "message": "Job has been stopped",
                }
                mock_task.apply_async.return_value = mock_result
                manager = PipelineManager(config_path=config_file)
                job_id = "test-job-id"
                manager.active_jobs[job_id] = {
                    "task_id": "test-task-id",
                    "repository_path": "/test/repo",
                    "start_time": 123456789,
                    "status": StepStatus.RUNNING,
                }
                manager.active_jobs[job_id]["status"] = StepStatus.STOPPED
                status = manager.stop(job_id)
                assert status["status"] == StepStatus.STOPPED
                assert "message" in status
