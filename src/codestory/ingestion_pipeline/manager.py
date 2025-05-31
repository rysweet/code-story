"""Pipeline manager for orchestrating ingestion workflows.

This module provides the PipelineManager class that handles discovery and
execution of ingestion workflow steps.
"""
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, cast
from .step import PipelineStep, StepStatus
from .tasks import get_job_status, orchestrate_pipeline, stop_job
from .utils import discover_pipeline_steps, find_step_manually, load_pipeline_config, record_job_metrics
logger = logging.getLogger(__name__)

class PipelineManager:
    """Manages the ingestion pipeline workflow.

    This class handles the discovery and execution of workflow steps,
    tracking their status, and providing methods to start, stop, and
    monitor ingestion jobs.
    """

    def __init__(self: Any, config_path: str | Path='pipeline_config.yml') -> None:
        """Initialize the pipeline manager.

        Args:
            config_path: Path to the pipeline configuration YAML file

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration file is invalid
        """
        self.config = load_pipeline_config(config_path)
        logger.info(f'Loaded pipeline configuration from {config_path}')
        self.steps = discover_pipeline_steps()
        logger.info(f'Discovered {len(self.steps)} pipeline steps')
        self.active_jobs: dict[str, dict[str, Any]] = {}

    def _get_step_class(self: Any, step_name: str) -> type[PipelineStep] | None:
        """Get the step class for a step name.

        First tries to find the step in the discovered entry points,
        then falls back to manual discovery.

        Args:
            step_name: Name of the step

        Returns:
            Optional[Type[PipelineStep]]: Step class if found, None otherwise
        """
        if step_name in self.steps:
            return cast(type[PipelineStep], self.steps[step_name])
        step_class = find_step_manually(step_name)
        if step_class:
            self.steps[step_name] = step_class
            return step_class
        return None

    def _prepare_step_configs(self: Any) -> list[dict[str, Any]]:
        """Prepare step configurations from the loaded config.

        Returns:
            List[Dict[str, Any]]: List of step configurations
        """
        step_configs = []
        for step in self.config['steps']:
            step_config = {'name': step['name']}
            for key, value in step.items():
                if key != 'name':
                    step_config[key] = value
            if 'steps' in self.config and step['name'] in self.config['steps']:
                step_config.update(self.config['steps'][step['name']])
            step_configs.append(step_config)
        return step_configs

    def _validate_steps(self: Any) -> None:
        """Validate that all configured steps exist.

        Raises:
            ValueError: If any configured step is not found
        """
        missing_steps = []
        for step in self.config['steps']:
            step_name = step['name']
            if not self._get_step_class(step_name):
                missing_steps.append(step_name)
        if missing_steps:
            raise ValueError(f"The following pipeline steps are configured but not found: {', '.join(missing_steps)}")

    def start_job(self: Any, repository_path: str) -> str:
        """Start a new ingestion job.

        Args:
            repository_path: Path to the repository to process

        Returns:
            str: Job ID for tracking

        Raises:
            ValueError: If steps are missing or repository path is invalid
        """
        if not os.path.isdir(repository_path):
            raise ValueError(f'Repository path does not exist: {repository_path}')
        self._validate_steps()
        job_id = str(uuid.uuid4())
        step_configs = self._prepare_step_configs()
        record_job_metrics(StepStatus.RUNNING)
        task = orchestrate_pipeline.apply_async(args=[repository_path, step_configs, job_id])
        self.active_jobs[job_id] = {'task_id': task.id, 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING}
        logger.info(f'Started ingestion job {job_id} for {repository_path}')
        return job_id

    def status(self: Any, job_id: str) -> dict[str, Any]:
        """Check the status of an ingestion job.

        Args:
            job_id: Job ID returned by start_job

        Returns:
            Dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        if job_id not in self.active_jobs:
            raise ValueError(f'Job ID not found: {job_id}')
        job_info = self.active_jobs[job_id]
        task_id = job_info['task_id']
        status_task = get_job_status.apply_async(args=[task_id])
        status_result = cast(dict[str, Any], status_task.get(timeout=30))
        job_info.update(status_result)
        if status_result['status'] in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.STOPPED):
            job_info['end_time'] = time.time()
            job_info['duration'] = job_info['end_time'] - job_info['start_time']
        return cast(dict[str, Any], job_info)

    def stop(self: Any, job_id: str) -> dict[str, Any]:
        """Stop an ingestion job.

        Args:
            job_id: Job ID returned by start_job

        Returns:
            Dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        if job_id not in self.active_jobs:
            raise ValueError(f'Job ID not found: {job_id}')
        job_info = self.active_jobs[job_id]
        task_id = job_info['task_id']
        stop_task = stop_job.apply_async(args=[task_id])
        stop_result = cast(dict[str, Any], stop_task.get(timeout=30))
        job_info.update(stop_result)
        record_job_metrics(StepStatus.STOPPED)
        return cast(dict[str, Any], job_info)

    def cancel(self: Any, job_id: str) -> dict[str, Any]:
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
            raise ValueError(f'Job ID not found: {job_id}')
        job_info = self.active_jobs[job_id]
        task_id = job_info['task_id']
        stop_task = stop_job.apply_async(args=[task_id])
        stop_result = cast(dict[str, Any], stop_task.get(timeout=30))
        if stop_result['status'] == StepStatus.STOPPED:
            stop_result['status'] = StepStatus.CANCELLED
        job_info.update(stop_result)
        record_job_metrics(StepStatus.CANCELLED)
        return cast(dict[str, Any], job_info)

    def run_single_step(self: Any, repository_path: str, step_name: str, **step_config: Any) -> str:
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
        if not os.path.isdir(repository_path):
            raise ValueError(f'Repository path does not exist: {repository_path}')
        step_class = self._get_step_class(step_name)
        if not step_class:
            raise ValueError(f'Step not found: {step_name}')
        job_id = str(uuid.uuid4())
        step = step_class()
        step_job_id = step.run(repository_path, **step_config)
        self.active_jobs[job_id] = {'task_id': step_job_id, 'repository_path': repository_path, 'step_name': step_name, 'start_time': time.time(), 'status': StepStatus.RUNNING}
        logger.info(f'Started single step {step_name} as job {job_id} for {repository_path}')
        return job_id