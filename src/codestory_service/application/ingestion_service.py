"""Ingestion service for Code Story Service.

This module provides application-level services for managing the ingestion pipeline,
including starting, stopping, and monitoring ingestion jobs.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from fastapi import Depends, HTTPException, WebSocket, status
import redis.asyncio as redis

from ..domain.ingestion import (
    IngestionRequest,
    IngestionStarted,
    StepProgress,
    IngestionJob,
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

            self.redis = redis.Redis(
                host=redis_host, port=redis_port, db=redis_db, decode_responses=True
            )

            # Ping Redis to verify connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
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

        try:
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
            logger.error(f"Failed to publish progress event: {str(e)}")

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

        try:
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
                except asyncio.TimeoutError:
                    # Send heartbeat on timeout
                    await websocket.send_json({"type": "heartbeat"})
                except Exception as e:
                    logger.error(f"Error in WebSocket communication: {str(e)}")
                    break

            # Unsubscribe and close
            await pubsub.unsubscribe(channel)
            await pubsub.close()

        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
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
                timestamp=ingestion_started.eta if ingestion_started.eta else None,
            )

            await self.publish_progress(ingestion_started.job_id, initial_event)

            return ingestion_started
        except Exception as e:
            logger.error(f"Failed to start ingestion: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
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
            logger.info(f"Getting status for job: {job_id}")

            # Get job status from the Celery adapter
            job = await self.celery.get_job_status(job_id)

            return job
        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
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
                timestamp=job.updated_at if job.updated_at else None,
            )

            await self.publish_progress(job_id, cancel_event)

            return job
        except Exception as e:
            logger.error(f"Failed to cancel job: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel job: {str(e)}",
            )

    async def list_jobs(
        self,
        status: Optional[List[JobStatus]] = None,
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
            logger.error(f"Failed to list jobs: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list jobs: {str(e)}",
            )


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
