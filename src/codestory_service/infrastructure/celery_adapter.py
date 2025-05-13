"""Celery adapter for the Code Story Service.

This module provides a service-specific adapter for Celery operations,
facilitating interaction with the ingestion pipeline and other background tasks.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status

from codestory.ingestion_pipeline.celery_app import app as celery_app
from codestory.ingestion_pipeline.tasks import (
    orchestrate_pipeline as run_ingestion_pipeline,
)
from codestory.ingestion_pipeline.tasks import run_step as run_single_step

from ..domain.ingestion import (
    IngestionRequest,
    IngestionStarted,
    IngestionJob,
    JobStatus,
)

# Set up logging
logger = logging.getLogger(__name__)


class CeleryAdapter:
    """Adapter for Celery operations specific to the service layer.

    This class provides methods for submitting tasks to Celery,
    checking task status, and revoking tasks.
    """

    def __init__(self) -> None:
        """Initialize the Celery adapter."""
        self.app = celery_app

    async def check_health(self) -> Dict[str, Any]:
        """Check Celery worker health.

        Returns:
            Dictionary containing health information
        """
        try:
            # Perform a simple ping to check if Celery is responsive
            inspector = self.app.control.inspect()
            active_workers = inspector.active()
            registered_workers = inspector.registered()

            if not active_workers and not registered_workers:
                return {
                    "status": "unhealthy",
                    "details": {
                        "error": "No active Celery workers found",
                        "type": "CeleryHealthCheckError",
                    },
                }

            return {
                "status": "healthy",
                "details": {
                    "active_workers": len(active_workers) if active_workers else 0,
                    "registered_tasks": len(registered_workers)
                    if registered_workers
                    else 0,
                },
            }
        except Exception as e:
            logger.error(f"Celery health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "details": {"error": str(e), "type": type(e).__name__},
            }

    async def start_ingestion(self, request: IngestionRequest) -> IngestionStarted:
        """Start an ingestion pipeline job.

        Args:
            request: Details of the ingestion request

        Returns:
            IngestionStarted with job ID and status

        Raises:
            HTTPException: If starting the ingestion job fails
        """
        try:
            # Convert domain model to task parameters
            task_params = {
                "source_type": request.source_type.value,
                "source": request.source,
                "options": request.options or {},
                "steps": request.steps or [],
                "metadata": {
                    "created_by": request.created_by,
                    "description": request.description,
                    "tags": request.tags,
                },
            }

            # Submit the Celery task
            # For testing, use a local reference that can be mocked
            task_func = getattr(self, "_run_ingestion_pipeline", run_ingestion_pipeline)
            task = task_func.apply_async(
                kwargs=task_params,
                countdown=0,  # Start immediately
                expires=3600 * 24,  # Expire after 24 hours if not started
            )

            # Create response
            return IngestionStarted(
                job_id=task.id,
                status=JobStatus.PENDING,
                source=request.source,  # Add required source field
                steps=request.steps or ["default_pipeline"],  # Add required steps field
                message="Ingestion job submitted successfully",
                eta=int(time.time()),  # Immediate start
            )

        except Exception as e:
            logger.error(f"Failed to start ingestion job: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start ingestion: {str(e)}",
            )

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
            task = self.app.AsyncResult(job_id)

            if task.state == "PENDING":
                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.PENDING,
                    created_at=int(time.time()),  # We don't know the exact time
                    updated_at=int(time.time()),
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

                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.RUNNING,
                    created_at=info.get("created_at", int(time.time())),
                    updated_at=int(time.time()),
                    progress=progress,
                    current_step=current_step,
                    message=message,
                    result=None,
                    error=None,
                )

            if task.state == "SUCCESS":
                result = task.result or {}

                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    created_at=result.get("created_at", int(time.time() - 60)),
                    updated_at=int(time.time()),
                    progress=100.0,
                    current_step="Completed",
                    message="Ingestion completed successfully",
                    result=result,
                    error=None,
                )

            if task.state == "FAILURE":
                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    created_at=int(time.time() - 60),  # Estimate
                    updated_at=int(time.time()),
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
                    created_at=int(time.time() - 60),  # Estimate
                    updated_at=int(time.time()),
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
                created_at=int(time.time() - 60),  # Estimate
                updated_at=int(time.time()),
                progress=0.0,
                current_step=task.state,
                message=f"Unknown task state: {task.state}",
                result=None,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get job status: {str(e)}",
            )

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
            task = self.app.AsyncResult(job_id)

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
                    created_at=int(time.time() - 60),  # Estimate
                    updated_at=int(time.time()),
                    progress=100.0 if task.state == "SUCCESS" else 0.0,
                    current_step=task.state.capitalize(),
                    message=f"Job already in terminal state: {task.state}",
                    result=task.result if task.state == "SUCCESS" else None,
                    error=str(task.result) if task.state == "FAILURE" else None,
                )

            # Attempt to revoke the task
            self.app.control.revoke(job_id, terminate=True)

            # Return updated job status
            return IngestionJob(
                job_id=job_id,
                status=JobStatus.CANCELLING,
                created_at=int(time.time() - 60),  # Estimate
                updated_at=int(time.time()),
                progress=0.0,
                current_step="Cancelling",
                message="Job cancellation requested",
                result=None,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel job: {str(e)}",
            )

    async def list_jobs(
        self, status: Optional[List[JobStatus]] = None, limit: int = 10, offset: int = 0
    ) -> List[IngestionJob]:
        """List ingestion jobs with optional filtering by status.

        Args:
            status: List of job statuses to filter by
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
            logger.error(f"Failed to list jobs: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list jobs: {str(e)}",
            )


class DummyCeleryAdapter(CeleryAdapter):
    """Dummy Celery adapter for use when Celery is not available.
    
    This allows basic service functionality without Celery being available.
    """
    
    def __init__(self):
        """Initialize the dummy adapter."""
        logger.warning("Using DummyCeleryAdapter - Celery functionality will be limited")
        # Don't initialize the real Celery app

    async def check_health(self) -> Dict[str, Any]:
        """Return degraded health for demo purposes."""
        return {
            "status": "degraded",
            "details": {
                "message": "Celery worker unavailable - using dummy adapter for demo purposes",
                "active_workers": 0,
                "registered_tasks": 0,
            },
        }
    
    async def start_ingestion(self, request: IngestionRequest) -> IngestionStarted:
        """Simulate starting an ingestion pipeline job.
        
        Args:
            request: Details of the ingestion request
            
        Returns:
            IngestionStarted with job ID and status
        """
        logger.info(f"DummyCeleryAdapter.start_ingestion called with source: {request.source}")
        
        # Generate a dummy job ID
        job_id = f"dummy-{int(time.time())}"
        
        return IngestionStarted(
            job_id=job_id,
            status=JobStatus.PENDING,
            source=request.source,
            steps=request.steps or ["default_pipeline"],
            message="Ingestion job submitted (dummy mode - no actual processing)",
            eta=int(time.time()),
        )
    
    async def get_job_status(self, job_id: str) -> IngestionJob:
        """Get the status of a dummy ingestion job.
        
        Args:
            job_id: ID of the ingestion job
            
        Returns:
            IngestionJob with dummy status information
        """
        logger.info(f"DummyCeleryAdapter.get_job_status called for job: {job_id}")
        
        # Determine status based on job_id format
        if job_id.startswith("dummy-"):
            # For demo purposes, return a running status for recent jobs
            timestamp = int(job_id.split("-")[1]) if len(job_id.split("-")) > 1 else 0
            current_time = int(time.time())
            
            if current_time - timestamp < 30:
                # Job is "running" for the first 30 seconds
                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.RUNNING,
                    created_at=timestamp,
                    updated_at=current_time,
                    progress=min(100, (current_time - timestamp) * 3.3),  # Simulate progress
                    current_step="Processing (demo mode)",
                    message="Simulated job in progress",
                    result=None,
                    error=None,
                )
            else:
                # After 30 seconds, job is "completed"
                return IngestionJob(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    created_at=timestamp,
                    updated_at=current_time,
                    progress=100.0,
                    current_step="Completed",
                    message="Simulated job completed successfully",
                    result={"nodes_created": 42, "relationships_created": 120},
                    error=None,
                )
        
        # For unknown job IDs
        return IngestionJob(
            job_id=job_id,
            status=JobStatus.UNKNOWN,
            created_at=int(time.time() - 60),
            updated_at=int(time.time()),
            progress=0.0,
            current_step="Unknown",
            message="Unknown job ID (dummy mode)",
            result=None,
            error=None,
        )


async def get_celery_adapter() -> CeleryAdapter:
    """Factory function to create a Celery adapter.

    This is used as a FastAPI dependency.

    Returns:
        CeleryAdapter instance (real or dummy)
    """
    try:
        # Try to create a real adapter
        adapter = CeleryAdapter()
        # Check health to verify connection
        celery_health = await adapter.check_health()
        if celery_health["status"] == "healthy":
            return adapter
        # If not healthy, fall back to dummy
        logger.warning("Real Celery adapter not healthy")
        return DummyCeleryAdapter()
    except Exception as e:
        # Log the error but don't fail
        logger.warning(f"Failed to create real Celery adapter: {str(e)}")
        logger.warning("Falling back to dummy Celery adapter for demo purposes")
        
        # Return a dummy adapter instead
        return DummyCeleryAdapter()
