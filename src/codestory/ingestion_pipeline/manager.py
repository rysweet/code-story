"""Pipeline manager for orchestrating ingestion workflows.

This module provides the PipelineManager class that handles discovery and
execution of ingestion workflow steps.
"""

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .step import PipelineStep, StepStatus
from .tasks import get_job_status, orchestrate_pipeline, stop_job
from .utils import (
    discover_pipeline_steps,
    find_step_manually,
    load_pipeline_config,
    record_job_metrics,
)

# Set up logging
logger = logging.getLogger(__name__)


class PipelineManager:
    """Manages the ingestion pipeline workflow.

    This class handles the discovery and execution of workflow steps,
    tracking their status, and providing methods to start, stop, and
    monitor ingestion jobs.
    """

    def __init__(self, config_path: str | Path = "pipeline_config.yml"):
        """Initialize the pipeline manager.

        Args:
            config_path: Path to the pipeline configuration YAML file

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration file is invalid
        """
        # Load configuration
        self.config = load_pipeline_config(config_path)
        logger.info(f"Loaded pipeline configuration from {config_path}")

        # Discover available steps
        self.steps = discover_pipeline_steps()
        logger.info(f"Discovered {len(self.steps)} pipeline steps")

        # Active jobs
        self.active_jobs: dict[str, dict[str, Any]] = {}

    def _get_step_class(self, step_name: str) -> type[PipelineStep] | None:
        """Get the step class for a step name.

        First tries to find the step in the discovered entry points,
        then falls back to manual discovery.

        Args:
            step_name: Name of the step

        Returns:
            Optional[Type[PipelineStep]]: Step class if found, None otherwise
        """
        if step_name in self.steps:
            return self.steps[step_name]

        # Fall back to manual discovery
        step_class = find_step_manually(step_name)
        if step_class:
            # Add to discovered steps
            self.steps[step_name] = step_class
            return step_class

        return None

    def _prepare_step_configs(self) -> list[dict[str, Any]]:
        """Prepare step configurations from the loaded config.

        Returns:
            List[Dict[str, Any]]: List of step configurations
        """
        step_configs = []

        for step in self.config["steps"]:
            # Get the base configuration
            step_config = {"name": step["name"]}

            # Add any additional configuration for this step
            for key, value in step.items():
                if key != "name":
                    step_config[key] = value

            # Check if there are step-specific settings in ingestion.steps
            if "steps" in self.config and step["name"] in self.config["steps"]:
                # Update with step-specific settings
                step_config.update(self.config["steps"][step["name"]])

            step_configs.append(step_config)

        return step_configs

    def _validate_steps(self) -> None:
        """Validate that all configured steps exist.

        Raises:
            ValueError: If any configured step is not found
        """
        missing_steps = []

        for step in self.config["steps"]:
            step_name = step["name"]
            if not self._get_step_class(step_name):
                missing_steps.append(step_name)

        if missing_steps:
            raise ValueError(
                f"The following pipeline steps are configured but not found: "
                f"{', '.join(missing_steps)}"
            )

    def start_job(self, repository_path: str) -> str:
        """Start a new ingestion job.

        Args:
            repository_path: Path to the repository to process

        Returns:
            str: Job ID for tracking

        Raises:
            ValueError: If steps are missing or repository path is invalid
        """
        # Validate repository path
        if not os.path.isdir(repository_path):
            raise ValueError(f"Repository path does not exist: {repository_path}")

        # Validate that all steps exist
        self._validate_steps()

        # Generate a job ID
        job_id = str(uuid.uuid4())

        # Prepare step configurations
        step_configs = self._prepare_step_configs()

        # Record job start
        record_job_metrics(StepStatus.RUNNING)

        # Start the orchestrator task
        task = orchestrate_pipeline.apply_async(
            args=[repository_path, step_configs, job_id]
        )

        # Store job information
        self.active_jobs[job_id] = {
            "task_id": task.id,
            "repository_path": repository_path,
            "start_time": time.time(),
            "status": StepStatus.RUNNING,
        }

        logger.info(f"Started ingestion job {job_id} for {repository_path}")

        return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        """Check the status of an ingestion job.

        Args:
            job_id: Job ID returned by start_job

        Returns:
            Dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        if job_id not in self.active_jobs:
            raise ValueError(f"Job ID not found: {job_id}")

        job_info = self.active_jobs[job_id]
        task_id = job_info["task_id"]

        # Get status from Celery
        status_task = get_job_status.apply_async(args=[task_id])
        # Add timeout for robustness - this is not in a task so it's not affected by the anti-pattern
        status_result = status_task.get(timeout=30)

        # Update job info with latest status
        job_info.update(status_result)

        # If the job is complete, calculate duration
        if status_result["status"] in (
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.STOPPED,
        ):
            job_info["end_time"] = time.time()
            job_info["duration"] = job_info["end_time"] - job_info["start_time"]

        return job_info

    def stop(self, job_id: str) -> dict[str, Any]:
        """Stop an ingestion job.

        Args:
            job_id: Job ID returned by start_job

        Returns:
            Dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        if job_id not in self.active_jobs:
            raise ValueError(f"Job ID not found: {job_id}")

        job_info = self.active_jobs[job_id]
        task_id = job_info["task_id"]

        # Stop the job
        stop_task = stop_job.apply_async(args=[task_id])
        # Add timeout for robustness - this is not in a task so it's not affected by the anti-pattern
        stop_result = stop_task.get(timeout=30)

        # Update job info with stop result
        job_info.update(stop_result)

        # Record job stop
        record_job_metrics(StepStatus.STOPPED)

        return job_info

    def cancel(self, job_id: str) -> dict[str, Any]:
        """Cancel an ingestion job.

        This is functionally the same as stop() for Celery tasks.

        Args:
            job_id: Job ID returned by start_job

        Returns:
            Dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        if job_id not in self.active_jobs:
            raise ValueError(f"Job ID not found: {job_id}")

        job_info = self.active_jobs[job_id]
        task_id = job_info["task_id"]

        # Cancel the job (same as stop for Celery)
        stop_task = stop_job.apply_async(args=[task_id])
        # Add timeout for robustness - this is not in a task so it's not affected by the anti-pattern
        stop_result = stop_task.get(timeout=30)

        # Update status to CANCELLED instead of STOPPED
        if stop_result["status"] == StepStatus.STOPPED:
            stop_result["status"] = StepStatus.CANCELLED

        # Update job info with cancel result
        job_info.update(stop_result)

        # Record job cancellation
        record_job_metrics(StepStatus.CANCELLED)

        return job_info

    def run_single_step(
        self, repository_path: str, step_name: str, **step_config: Any
    ) -> str:
        """Run a single workflow step.

        This is useful for testing or running a step in isolation.

        Args:
            repository_path: Path to the repository to process
            step_name: Name of the step to run
            **step_config: Additional configuration for the step

        Returns:
            str: Job ID for tracking

        Raises:
            ValueError: If the step is not found or repository doesn't exist
        """
        # Validate repository path
        if not os.path.isdir(repository_path):
            raise ValueError(f"Repository path does not exist: {repository_path}")

        # Get the step class
        step_class = self._get_step_class(step_name)
        if not step_class:
            raise ValueError(f"Step not found: {step_name}")

        # Generate a job ID
        job_id = str(uuid.uuid4())

        # Instantiate the step
        step = step_class()

        # Run the step
        step_job_id = step.run(repository_path, **step_config)

        # Store job information
        self.active_jobs[job_id] = {
            "task_id": step_job_id,  # In this case, step_job_id might not be a Celery task ID
            "repository_path": repository_path,
            "step_name": step_name,
            "start_time": time.time(),
            "status": StepStatus.RUNNING,
        }

        logger.info(
            f"Started single step {step_name} as job {job_id} for {repository_path}"
        )

        return job_id
