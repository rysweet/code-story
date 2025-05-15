"""WebSocket endpoints for real-time updates.

This module provides WebSocket endpoints for real-time progress updates
and notifications.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from ..application.ingestion_service import IngestionService, get_ingestion_service

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/status/{job_id}")
async def job_status_websocket(
    websocket: WebSocket,
    job_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> None:
    """WebSocket endpoint for real-time job status updates.

    Args:
        websocket: WebSocket connection
        job_id: ID of the ingestion job to monitor
        ingestion_service: Ingestion service instance
    """
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection established for job: {job_id}")

        # Verify that the job exists
        try:
            # This will raise an exception if the job doesn't exist
            job = await ingestion_service.get_job_status(job_id)
            logger.info(f"Job {job_id} found with status: {job.status}")
        except Exception as e:
            logger.error(f"Job {job_id} not found: {str(e)}")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason=f"Job not found: {job_id}"
            )
            return

        # Subscribe to job status updates
        await ingestion_service.subscribe_to_progress(websocket, job_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job: {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {str(e)}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=str(e))
        except Exception:
            # WebSocket already closed
            pass
