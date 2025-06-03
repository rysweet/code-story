"""Celery adapter for the Code Story Service.

This module provides a service-specific adapter for Celery operations,
facilitating interaction with the ingestion pipeline and other background tasks.
"""

import logging
import os
import time
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from codestory.ingestion_pipeline.celery_app import app as celery_app
from codestory.ingestion_pipeline.tasks import (
    orchestrate_pipeline as run_ingestion_pipeline,
)

from ..domain.ingestion import (
    IngestionJob,
    IngestionRequest,
    IngestionStarted,
    JobStatus,
    StepProgress,
    StepStatus,
)

# Set up logging
logger = logging.getLogger(__name__)


class CeleryAdapter:
    @staticmethod
    def _safe_float(val: Any) -> float | None:
        try:
            if val is None or val == "":
                return None
            return float(val)
        except (TypeError, ValueError):
            return None

    """Adapter for Celery operations specific to the service layer.

    This class provides methods for submitting tasks to Celery,
    checking task status, and revoking tasks.
    """

    def __init__(self) -> None:
        """Initialize the Celery adapter."""
        self._app = celery_app

    async def check_health(self) -> tuple[str, dict[str, Any]]:
        """Check Celery worker health.

        Returns:
            Tuple containing (status, details) where status is "healthy" or "unhealthy"
        """
        try:
            # Early return if task_always_eager is enabled
            if (self._app.conf.task_always_eager is True or
                os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true")):
                return "healthy", {"message": "Eager mode enabled, no workers needed"}
            
            # Perform a simple ping to check if Celery is responsive
            inspector = self._app.control.inspect()
            active_workers = inspector.active()
            registered_workers = inspector.registered()

            if not active_workers and not registered_workers:
                return "unhealthy", {
                    "error": "No active Celery workers found",
                    "type": "CeleryHealthCheckError",
                }

            return "healthy", {
                "active_workers": len(active_workers) if active_workers else 0,
                "registered_tasks": len(registered_workers)
                if registered_workers
                else 0,
            }
        except Exception as e:
            logger.error(f"Celery health check failed: {e!s}")
            return "unhealthy", {"error": str(e), "type": type(e).__name__}

    async def start_ingestion(self, request: IngestionRequest) -> IngestionStarted:
        """Start an ingestion pipeline job.

        Args:
            request: Details of the ingestion request

        Returns:
            IngestionStarted with job ID and status

        Raises:
            HTTPException: If starting the ingestion job fails

        Notes:
            This method applies parameter filtering to ensure each pipeline step only
            receives parameters it can handle. Different steps have different parameter
            requirements, and parameter filtering prevents "unexpected keyword argument"
            errors when passing configuration between steps.

            Parameter filtering is applied as follows:
            - blarify: Excludes 'concurrency' parameter
            - summarizer/docgrapher: Only includes safe parameters ('job_id', 'ignore_patterns',
              'timeout', 'incremental') plus step-specific parameters
            - filesystem and other steps: Receives all parameters
        """
        try:
            # The orchestrate_pipeline task expects repository_path, step_configs, and job_id
            # We need to transform the IngestionRequest into these parameters

            # Use the source as the repository path
            repository_path = request.source

            # Generate a job_id
            from uuid import uuid4

            job_id = str(uuid4())

            # Create step configs
            step_configs: list[Any] = []
            if request.steps:
                for step_name in request.steps:
                    step_configs.append({"name": step_name})
            else:
                # Default steps if none provided
                for step_name in ["filesystem", "blarify", "summarizer", "docgrapher"]:
                    step_configs.append({"name": step_name})

            # Add options to each step if provided, with parameter filtering
            if request.options:
                for step_config in step_configs:
                    step_name = step_config["name"]

                    # Filter options based on step type to avoid parameter conflicts
                    if step_name == "blarify":
                        # Blarify step doesn't use certain parameters
                        filtered_options = {
                            k: v
                            for k, v in request.options.items()
                            if k not in ["concurrency"]
                        }
                        step_config.update(filtered_options)
                        logger.debug(
                            f"Applied filtered options for blarify step: {filtered_options}"
                        )

                    elif step_name in ["summarizer", "docgrapher"]:
                        # These steps have specific parameters
                        safe_params = [
                            "job_id",
                            "ignore_patterns",
                            "timeout",
                            "incremental",
                        ]
                        filtered_options = {
                            k: v
                            for k, v in request.options.items()
                            if k in safe_params or k == step_name + "_specific"
                        }
                        step_config.update(filtered_options)
                        logger.debug(
                            f"Applied filtered options for {step_name} step: {filtered_options}"
                        )

                    else:
                        # For filesystem and other steps, include all options
                        step_config.update(request.options)
                        logger.debug(f"Applied all options for {step_name} step")

            # Submit the Celery task with positional parameters
            # For testing, use a local reference that can be mocked
            task_func = getattr(self, "_run_ingestion_pipeline", run_ingestion_pipeline)
            # Map priority to queue name
            queue_name = (
                request.priority
                if request.priority in {"high", "default", "low"}
                else "default"
            )
            # Scheduling support: determine eta/countdown
            eta = None
            countdown = 0
            if getattr(request, "eta", None):
                # Accept both datetime and int (timestamp)
                if isinstance(request.eta, datetime):
                    eta = request.eta
                else:
                    try:
                        if request.eta is not None:
                            eta = datetime.fromtimestamp(int(request.eta))
                    except Exception:
                        eta = None
            elif getattr(request, "countdown", None):
                if request.countdown is not None:
                    countdown = int(request.countdown)

            task = task_func.apply_async(
                args=[repository_path, step_configs, job_id],
                queue=queue_name,
                eta=eta,
                countdown=countdown if eta is None else None,
                expires=3600 * 24,  # Expire after 24 hours if not started
            )

            # Create response
            return IngestionStarted(
                job_id=task.id,
                status=JobStatus.PENDING,
                source=request.source,  # Add required source field
                steps=request.steps or ["default_pipeline"],  # Add required steps field
                message="Ingestion job submitted successfully",
                eta=int(eta.timestamp())
                if eta
                else (int(time.time()) + countdown if countdown else int(time.time())),
            )

        except Exception as e:
            logger.error(f"Failed to start ingestion job: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start ingestion: {e!s}",
            ) from e

    async def get_job_status(self, job_id: str) -> IngestionJob:
        """Get the status of an ingestion job.

        Args:
            job_id: ID of the ingestion job

        Returns:
            IngestionJob with current status information

        Raises:
            HTTPException: If retrieving job status fails
        """
        try:
            # Check if job exists
            task = self._app.AsyncResult(job_id)

            # Helper to build steps dict from Celery result
            def build_steps_from_result(result: Any) -> dict[str, StepProgress]:
                steps = {}
                # If result is a list of step dicts (from orchestrate_pipeline)
                if (
                    isinstance(result, dict)
                    and "steps" in result
                    and isinstance(result["steps"], list)
                ):
                    for step in result["steps"]:
                        name = step.get("step") or step.get("name") or "unknown"
                        steps[name] = StepProgress(
                            name=name,
                            status=StepStatus(step.get("status", StepStatus.PENDING)),
                            progress=step.get("progress", 0.0),
                            message=step.get("message"),
                            error=step.get("error"),
                            started_at=(
                                datetime.fromtimestamp(start_time_val)
                                if (
                                    start_time_val := CeleryAdapter._safe_float(
                                        step.get("start_time")
                                    )
                                )
                                is not None
                                else None
                            ),
                            completed_at=(
                                datetime.fromtimestamp(end_time_val)
                                if (
                                    end_time_val := CeleryAdapter._safe_float(
                                        step.get("end_time")
                                    )
                                )
                                is not None
                                else None
                            ),
                            duration=step.get("duration"),
                            cpu_percent=step.get("cpu_percent"),
                            memory_mb=step.get("memory_mb"),
                            retry_count=step.get("retry_count"),
                            last_error=step.get("last_error"),
                        )
                # If result is a single step dict
                elif isinstance(result, dict) and "step" in result:
                    name = result.get("step") or result.get("name") or "unknown"
                    steps[name] = StepProgress(
                        name=name,
                        status=StepStatus(result.get("status", StepStatus.PENDING)),
                        progress=result.get("progress", 0.0),
                        message=result.get("message"),
                        error=result.get("error"),
                        started_at=(
                            datetime.fromtimestamp(start_time_val)
                            if (
                                start_time_val := CeleryAdapter._safe_float(
                                    result.get("start_time")
                                )
                            )
                            is not None
                            else None
                        ),
                        completed_at=(
                            datetime.fromtimestamp(end_time_val)
                            if (
                                end_time_val := CeleryAdapter._safe_float(
                                    result.get("end_time")
                                )
                            )
                            is not None
                            else None
                        ),
                        duration=result.get("duration"),
                        cpu_percent=result.get("cpu_percent"),
                        memory_mb=result.get("memory_mb"),
                        retry_count=result.get("retry_count"),
                        last_error=result.get("last_error"),
                    )
                return steps

            if task.state == "PENDING":
                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.PENDING,
                    source=None,
                    source_type=None,
                    branch=None,
                    created_at=int(time.time()),  # We don't know the exact time
                    updated_at=int(time.time()),
                    started_at=None,
                    completed_at=None,
                    duration=None,
                    steps=None,
                    progress=0.0,
                    current_step="Waiting to start",
                    message="Task is waiting for execution",
                    result=None,
                    error=None,
                )

            if task.state == "STARTED":
                # Try to get more detailed info from task.info if available
                info = task.info or {}
                progress = info.get("progress", 0.0)
                current_step = info.get("step", "Processing")
                message = info.get("message", "Task is in progress")
                steps = build_steps_from_result(info)

                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.RUNNING,
                    source=None,
                    source_type=None,
                    branch=None,
                    created_at=info.get("created_at", int(time.time())),
                    updated_at=int(time.time()),
                    started_at=None,
                    completed_at=None,
                    duration=None,
                    steps=steps,
                    progress=progress,
                    current_step=current_step,
                    message=message,
                    result=None,
                    error=None,
                )

            if task.state == "SUCCESS":
                result = task.result or {}
                steps = build_steps_from_result(result)
                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    source=None,
                    source_type=None,
                    branch=None,
                    created_at=result.get("created_at", int(time.time()) - 60),
                    updated_at=int(time.time()),
                    started_at=None,
                    completed_at=None,
                    duration=None,
                    steps=steps,
                    progress=100.0,
                    current_step="Completed",
                    message="Ingestion completed successfully",
                    result=result,
                    error=None,
                )

            if task.state == "FAILURE":
                info = task.info or {}
                steps = build_steps_from_result(info)
                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    source=None,
                    source_type=None,
                    branch=None,
                    created_at=int(time.time()) - 60,  # Estimate
                    updated_at=int(time.time()),
                    started_at=None,
                    completed_at=None,
                    duration=None,
                    steps=steps,
                    progress=0.0,
                    current_step="Failed",
                    message=str(task.result) if task.result else "Task failed",
                    result=None,
                    error=str(task.result) if task.result else "Unknown error",
                )

            if task.state == "REVOKED":
                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.CANCELLED,
                    source=None,
                    source_type=None,
                    branch=None,
                    created_at=int(time.time()) - 60,  # Estimate
                    updated_at=int(time.time()),
                    started_at=None,
                    completed_at=None,
                    duration=None,
                    steps=None,
                    progress=0.0,
                    current_step="Cancelled",
                    message="Task was cancelled",
                    result=None,
                    error=None,
                )

            # Default case for unknown state
            return IngestionJob(
                job_id=job_id,
                status=JobStatus.UNKNOWN,
                source=None,
                source_type=None,
                branch=None,
                created_at=int(time.time()) - 60,  # Estimate
                updated_at=int(time.time()),
                started_at=None,
                completed_at=None,
                duration=None,
                steps=None,
                progress=0.0,
                current_step=task.state,
                message=f"Unknown task state: {task.state}",
                result=None,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get job status: {e!s}",
            ) from e

    async def cancel_job(self, job_id: str) -> IngestionJob:
        """Cancel an ingestion job.

        Args:
            job_id: ID of the ingestion job to cancel

        Returns:
            IngestionJob with updated status

        Raises:
            HTTPException: If cancelling the job fails
        """
        try:
            # Check if job exists
            task = self._app.AsyncResult(job_id)

            if task.state in ["SUCCESS", "FAILURE", "REVOKED"]:
                # Job is already in a terminal state
                status_map = {
                    "SUCCESS": JobStatus.COMPLETED,
                    "FAILURE": JobStatus.FAILED,
                    "REVOKED": JobStatus.CANCELLED,
                }

                return IngestionJob(
                    job_id=job_id,
                    status=status_map.get(task.state, JobStatus.UNKNOWN),
                    source=None,
                    source_type=None,
                    branch=None,
                    started_at=None,
                    completed_at=None,
                    duration=None,
                    steps=None,
                    created_at=int(time.time() - 60),  # Estimate
                    updated_at=int(time.time()),
                    progress=100.0 if task.state == "SUCCESS" else 0.0,
                    current_step=task.state.capitalize(),
                    message=f"Job already in terminal state: {task.state}",
                    result=task.result if task.state == "SUCCESS" else None,
                    error=str(task.result) if task.state == "FAILURE" else None,
                )

            # Attempt to revoke the task
            self._app.control.revoke(job_id, terminate=True)

            # Return updated job status
            return IngestionJob(
                job_id=job_id,
                status=JobStatus.CANCELLING,
                source=None,
                source_type=None,
                branch=None,
                created_at=int(time.time()) - 60,  # Estimate
                updated_at=int(time.time()),
                started_at=None,
                completed_at=None,
                duration=None,
                steps=None,
                progress=0.0,
                current_step="Cancelling",
                message="Job cancellation requested",
                result=None,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel job: {e!s}",
            ) from e

    async def list_jobs(
        self, statuses: list[JobStatus] | None = None, limit: int = 10, offset: int = 0
    ) -> list[IngestionJob]:
        """List ingestion jobs with optional filtering by status.

        Args:
            statuses: List of job statuses to filter by
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip

        Returns:
            List of IngestionJob objects

        Raises:
            HTTPException: If listing jobs fails
        """
        try:
            # This implementation is a placeholder since Celery doesn't provide
            # a direct way to list all tasks. In a production environment, we would
            # need to store job information in a database for proper querying.

            # Simulate job listing for demo purposes
            # In a real implementation, we would query a database
            # where we've stored task metadata

            # This is a stub implementation
            return []

        except Exception as e:
            logger.error(f"Failed to list jobs: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list jobs: {e!s}",
            ) from e


# DummyCeleryAdapter has been removed as Celery is now a required component
# The service will fail if Celery is not available


async def get_celery_adapter() -> CeleryAdapter:
    """Factory function to create a Celery adapter.

    This is used as a FastAPI dependency.

    Returns:
        CeleryAdapter instance

    Raises:
        RuntimeError: If Celery is not available or not healthy
    """
    try:
        # Try to create a real adapter
        adapter = CeleryAdapter()
        
        # Skip health check if eager mode is enabled
        if (adapter._app.conf.task_always_eager is True or
            os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true")):
            # In eager mode, forcibly set a dummy backend to avoid Redis connection attempts
            adapter._app.conf.result_backend = "cache+memory://"
            return adapter
        
        # Check health to verify connection
        status, details = await adapter.check_health()
        if status == "healthy":
            return adapter
        # If not healthy, raise an exception
        if isinstance(details, dict):
            error_msg = details.get("error", "No active Celery workers found")
        else:
            error_msg = str(details)
        logger.error(f"Celery adapter not healthy: {error_msg}")
        raise RuntimeError(f"Celery component unhealthy: {error_msg}")
    except Exception as e:
        # Log the error and fail
        logger.error(f"Failed to create Celery adapter: {e!s}")
        raise RuntimeError(f"Celery component required but unavailable: {e!s}") from e
