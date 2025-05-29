"""Ingestion service for Code Story Service.

This module provides application-level services for managing the ingestion pipeline,
including starting, stopping, and monitoring ingestion jobs.
"""

import asyncio
import json
import logging
import time

import redis.asyncio as redis
from fastapi import Depends, HTTPException, WebSocket, status

from ..domain.ingestion import (
    IngestionJob,
    IngestionRequest,
    IngestionStarted,
    JobProgressEvent,
    JobStatus,
    PaginatedIngestionJobs,
)
from ..infrastructure.celery_adapter import CeleryAdapter, get_celery_adapter
from ..settings import get_service_settings

# Set up logging
logger = logging.getLogger(__name__)


class IngestionService:
    """Application service for ingestion pipeline operations.

    This service orchestrates interactions with the ingestion pipeline,
    providing high-level methods for the API layer and managing
    real-time progress updates via Redis PubSub.
    """

    def __init__(self, celery_adapter: CeleryAdapter) -> None:
        """Initialize the ingestion service.

        Args:
            celery_adapter: Celery adapter instance
        """
        self.celery = celery_adapter
        self.settings = get_service_settings()

        # Initialize Redis connection for real-time updates
        self.redis = None
        self.pubsub_channel = "codestory:ingestion:progress"

        # Don't try to connect to Redis during test initialization
        # In production code, we would use asyncio.create_task
        self._init_redis_task = None

    async def _init_redis(self) -> None:
        """Initialize Redis connection asynchronously."""
        try:
            # Get Redis connection details from core settings
            # In a real implementation, these would be retrieved from settings
            redis_host = "localhost"
            redis_port = 6379
            redis_db = 0

            self.redis = redis.Redis(  # type: ignore  # TODO: Fix type compatibility
                host=redis_host, port=redis_port, db=redis_db, decode_responses=True
            )

            # Ping Redis to verify connection
            await self.redis.ping()  # type: ignore[attr-defined]
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e!s}")
            self.redis = None

    async def publish_progress(self, job_id: str, event: JobProgressEvent) -> None:
        """Publish a progress event to Redis PubSub.

        Args:
            job_id: ID of the ingestion job
            event: Progress event details

        Raises:
            RuntimeError: If Redis is not available
        """
        if not self.redis:
            logger.warning("Redis not available for publishing progress")
            return

        try:  # type: ignore[unreachable]
            # Create channel name specific to this job
            channel = f"{self.pubsub_channel}:{job_id}"

            # Serialize event to JSON
            event_json = json.dumps(event.model_dump())

            # Publish to Redis
            await self.redis.publish(channel, event_json)

            # Also store the latest event in a Redis key for retrieval
            key = f"codestory:ingestion:latest:{job_id}"
            await self.redis.set(key, event_json, ex=3600 * 24)  # Expire after 24 hours
        except Exception as e:
            logger.error(f"Failed to publish progress event: {e!s}")

    async def subscribe_to_progress(self, websocket: WebSocket, job_id: str) -> None:
        """Subscribe to progress events for a job via WebSocket.

        Args:
            websocket: WebSocket connection to send events to
            job_id: ID of the ingestion job to monitor

        Raises:
            HTTPException: If Redis is not available
        """
        if not self.redis:
            logger.error("Redis not available for progress subscription")
            await websocket.close(code=1011, reason="Service unavailable")
            return

        try:  # type: ignore[unreachable]
            # Create channel name specific to this job
            channel = f"{self.pubsub_channel}:{job_id}"

            # Get the latest event from Redis
            key = f"codestory:ingestion:latest:{job_id}"
            latest_event = await self.redis.get(key)

            if latest_event:
                # Send the latest event immediately
                await websocket.send_text(latest_event)

            # Subscribe to the channel
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)

            # Listen for messages
            while True:
                try:
                    # Add heartbeat/timeout to prevent connections from hanging
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=self.settings.websocket_heartbeat,
                    )

                    if message and message["type"] == "message":
                        # Forward the message to the WebSocket
                        await websocket.send_text(message["data"])
                    else:
                        # Send heartbeat
                        await websocket.send_json({"type": "heartbeat"})
                except TimeoutError:
                    # Send heartbeat on timeout
                    await websocket.send_json({"type": "heartbeat"})
                except Exception as e:
                    logger.error(f"Error in WebSocket communication: {e!s}")
                    break

            # Unsubscribe and close
            await pubsub.unsubscribe(channel)
            await pubsub.close()

        except Exception as e:
            logger.error(f"WebSocket error: {e!s}")
            if websocket.client_state.CONNECTED:
                await websocket.close(code=1011, reason=str(e))

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
            logger.info(f"Starting ingestion for source: {request.source}")

            # Initialize Redis if not already done
            if self.redis is None:
                await self._init_redis()

            # Dependency-aware job scheduling
            dependencies = getattr(request, "dependencies", None)
            job_id = None

            if dependencies:
                # Store the job as waiting in Redis with its dependencies
                job_id = f"job-{int(time.time() * 1000)}"
                waiting_key = f"codestory:ingestion:waiting:{job_id}"
                await self.redis.set(
                    waiting_key,
                    json.dumps({
                        "request": request.model_dump(),
                        "dependencies": dependencies,
                        "status": "waiting"
                    }),
                    ex=3600 * 24
                )
                logger.info(f"Job {job_id} is waiting for dependencies: {dependencies}")

                # Publish initial progress event
                from codestory.ingestion_pipeline.step import StepStatus
                initial_event = JobProgressEvent(
                    job_id=job_id,
                    step="WaitingForDependencies",
                    status=StepStatus.PENDING,
                    progress=0.0,
                    overall_progress=0.0,
                    message=f"Waiting for dependencies: {dependencies}",
                    cpu_percent=None,
                    memory_mb=None,
                    timestamp=time.time(),
                )
                await self.publish_progress(job_id, initial_event)

                # Return a placeholder IngestionStarted object
                return IngestionStarted(
                    job_id=job_id,
                    status=JobStatus.PENDING,
                    source=request.source,
                    # started_at is optional, so omit it if not available
                    steps=request.steps or [],
                    message=f"Job is waiting for dependencies: {dependencies}",
                    eta=None,
                )
            else:
                # Start the job using the Celery adapter
                ingestion_started = await self.celery.start_ingestion(request)

                # Publish initial progress event
                from codestory.ingestion_pipeline.step import StepStatus

                initial_event = JobProgressEvent(
                    job_id=ingestion_started.job_id,
                    step="Initializing",
                    status=StepStatus.PENDING,
                    progress=0.0,
                    overall_progress=0.0,
                    message="Preparing to start ingestion",
                    cpu_percent=None,
                    memory_mb=None,
                    timestamp=ingestion_started.eta if ingestion_started.eta else None,  # type: ignore[arg-type]
                )

                await self.publish_progress(ingestion_started.job_id, initial_event)

                return ingestion_started
        except Exception as e:
            logger.error(f"Failed to start ingestion: {e!s}")
            if isinstance(e, HTTPException):
                raise e
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
            logger.info(f"Getting status for job: {job_id}")

            # Get job status from the Celery adapter
            job = await self.celery.get_job_status(job_id)

            # If job is completed, check for dependent jobs
            if job.status == JobStatus.COMPLETED:
                await self._check_and_trigger_dependents(job_id)

            return job
        except Exception as e:
            logger.error(f"Failed to get job status: {e!s}")
            if isinstance(e, HTTPException):
                raise e
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
            logger.info(f"Cancelling job: {job_id}")

            # Cancel the job using the Celery adapter
            job = await self.celery.cancel_job(job_id)

            # Publish cancellation event
            from codestory.ingestion_pipeline.step import StepStatus

            cancel_event = JobProgressEvent(
                job_id=job_id,
                step=job.current_step if job.current_step else "Cancelled",
                status=StepStatus.CANCELLED,
                progress=0.0,
                overall_progress=job.progress,
                message="Job was cancelled by user",
                cpu_percent=None,
                memory_mb=None,
                timestamp=job.updated_at if job.updated_at else None,  # type: ignore[arg-type]
            )

            await self.publish_progress(job_id, cancel_event)

            return job
        except Exception as e:
            logger.error(f"Failed to cancel job: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel job: {e!s}",
            ) from e

    async def list_jobs(
        self,
        status: list[JobStatus] | None = None,
        limit: int = 10,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaginatedIngestionJobs:
        """List ingestion jobs with optional filtering.

        Args:
            status: List of job statuses to filter by
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            sort_by: Field to sort by
            sort_order: Sort direction ("asc" or "desc")

        Returns:
            PaginatedIngestionJobs with list of jobs

        Raises:
            HTTPException: If listing jobs fails
        """
        try:
            logger.info(f"Listing jobs with status filter: {status}")

            # Get jobs from the Celery adapter
            jobs = await self.celery.list_jobs(status, limit, offset)

            # In a real implementation, we would also get the total count
            # and properly implement pagination. This is a placeholder.
            total = len(jobs)

            return PaginatedIngestionJobs(
                items=jobs,
                total=total,
                limit=limit,
                offset=offset,
                has_more=False,  # Placeholder
            )
        except Exception as e:
            logger.error(f"Failed to list jobs: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # type: ignore[union-attr]
                detail=f"Failed to list jobs: {e!s}",
            ) from e


    async def get_resource_status(self) -> dict:
        """
        Return current resource token status for ingestion throttling.
    
        Plus recent job metrics (duration, CPU %, memory MB).
        """
        from codestory.config.settings import get_settings
        from codestory.ingestion_pipeline.resource_manager import ResourceTokenManager
    
        # Token status
        settings = get_settings()
        redis_url = settings.redis.uri
        max_tokens = getattr(settings.ingestion, "resource_max_tokens", 4)
        token_manager = ResourceTokenManager(
            redis_url=redis_url,
            max_tokens=max_tokens,
        )
        token_status = token_manager.get_status()
    
        # Recent job metrics
        try:
            jobs = await self.celery.list_jobs(limit=20)
        except Exception as e:
            jobs = []
            logger.error(f"Failed to fetch recent jobs for metrics: {e!s}")
    
        durations = []
        cpu_percents = []
        memory_mbs = []
    
        for job in jobs:
            # Job-level metrics
            if getattr(job, "duration", None) is not None:
                durations.append(job.duration)
            # Step-level metrics (cpu_percent, memory_mb, duration)
            steps = getattr(job, "steps", None)
            if steps and isinstance(steps, dict):
                for step in steps.values():
                    if getattr(step, "duration", None) is not None:
                        durations.append(step.duration)
                    if getattr(step, "cpu_percent", None) is not None:
                        cpu_percents.append(step.cpu_percent)
                    if getattr(step, "memory_mb", None) is not None:
                        memory_mbs.append(step.memory_mb)
    
        def summary_stats(values):
            if not values:
                return {"avg": None, "min": None, "max": None}
            return {
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            }
    
        metrics_summary = {
            "job_count": len(jobs),
            "duration_seconds": summary_stats(durations),
            "cpu_percent": summary_stats(cpu_percents),
            "memory_mb": summary_stats(memory_mbs),
        }
    
        return {
            "tokens": token_status,
            "metrics": metrics_summary,
        }


    async def _check_and_trigger_dependents(self, completed_job_id: str) -> None:
        """Check for jobs waiting on this job and enqueue if all dependencies are complete."""
        if self.redis is None:
            await self._init_redis()
        # Scan for all waiting jobs
        pattern = "codestory:ingestion:waiting:*"
        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.get(key)
            if not data:
                continue
            try:
                job_info = json.loads(data)
                dependencies = job_info.get("dependencies", [])
                if completed_job_id in dependencies:
                    # Check if all dependencies are now complete
                    all_complete = True
                    for dep in dependencies:
                        status_key = f"codestory:ingestion:latest:{dep}"
                        dep_event = await self.redis.get(status_key)
                        if not dep_event:
                            all_complete = False
                            break
                        dep_event_data = json.loads(dep_event)
                        dep_status = dep_event_data.get("status", None)
                        if dep_status not in ("completed", JobStatus.COMPLETED):
                            all_complete = False
                            break
                    if all_complete:
                        # All dependencies are complete, dequeue and enqueue the job
                        request_data = job_info["request"]
                        # Remove from waiting
                        await self.redis.delete(key)
                        # Enqueue the job
                        logger.info(f"All dependencies complete for waiting job, enqueuing: {key}")
                        req = IngestionRequest(**request_data)
                        await self.start_ingestion(req)
            except Exception as e:
                logger.error(f"Error checking/enqueuing dependent job for {completed_job_id}: {e!s}")

async def get_ingestion_service(
    celery: CeleryAdapter = Depends(get_celery_adapter),
) -> IngestionService:
    """Factory function to create an ingestion service.
    
    This is used as a FastAPI dependency.
    
    Args:
        celery: Celery adapter instance
    
    Returns:
        IngestionService instance
    """
    return IngestionService(celery)