"""API routes for ingestion pipeline operations.

This module provides endpoints for starting, monitoring, and managing
ingestion pipeline jobs.
"""

import contextlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status

from ..application.ingestion_service import IngestionService, get_ingestion_service
from ..domain.ingestion import (
    IngestionJob,
    IngestionRequest,
    IngestionStarted,
    JobStatus,
    PaginatedIngestionJobs,
)
from ..infrastructure.msal_validator import get_current_user

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])


@router.post(
    "",
    response_model=IngestionStarted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an ingestion job",
    description="Start a new ingestion pipeline job with the specified source and options.",
)
async def start_ingestion(
    request: IngestionRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: dict = Depends(get_current_user),
) -> IngestionStarted:
    """Start an ingestion pipeline job.

    Args:
        request: Details of the ingestion request
        ingestion_service: Ingestion service instance
        user: Current authenticated user

    Returns:
        IngestionStarted with job ID and status

    Raises:
        HTTPException: If starting the ingestion job fails
    """
    # Add user information to the request
    request.created_by = user.get("name", "unknown")

    try:
        logger.info(f"Starting ingestion for source: {request.source}")
        return await ingestion_service.start_ingestion(request)
    except Exception as e:
        logger.error(f"Failed to start ingestion: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start ingestion: {e!s}",
        ) from e


@router.get(
    "",
    response_model=PaginatedIngestionJobs,
    summary="List ingestion jobs",
    description="Get a paginated list of ingestion jobs with optional filtering by status.",
)
async def list_jobs(
    status: list[JobStatus] | None = Query(None, description="Filter by job status"),
    limit: int = Query(10, description="Maximum number of jobs to return"),
    offset: int = Query(0, description="Number of jobs to skip"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort direction (asc or desc)"),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: dict = Depends(get_current_user),
) -> PaginatedIngestionJobs:
    """List ingestion jobs with optional filtering.

    Args:
        status: List of job statuses to filter by
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        sort_by: Field to sort by
        sort_order: Sort direction ("asc" or "desc")
        ingestion_service: Ingestion service instance
        user: Current authenticated user

    Returns:
        PaginatedIngestionJobs with list of jobs

    Raises:
        HTTPException: If listing jobs fails
    """
    try:
        logger.info(f"Listing jobs with status filter: {status}")
        return await ingestion_service.list_jobs(
            status=status,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        logger.error(f"Failed to list jobs: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {e!s}",
        ) from e


@router.get(
    "/{job_id}",
    response_model=IngestionJob,
    summary="Get job status",
    description="Get the current status of an ingestion job.",
)
async def get_job_status(
    job_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: dict = Depends(get_current_user),
) -> IngestionJob:
    """Get the status of an ingestion job.

    Args:
        job_id: ID of the ingestion job
        ingestion_service: Ingestion service instance
        user: Current authenticated user

    Returns:
        IngestionJob with current status information

    Raises:
        HTTPException: If retrieving job status fails
    """
    try:
        logger.info(f"Getting status for job: {job_id}")
        return await ingestion_service.get_job_status(job_id)
    except Exception as e:
        logger.error(f"Failed to get job status: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {e!s}",
        ) from e


@router.post(
    "/{job_id}/cancel",
    response_model=IngestionJob,
    summary="Cancel job",
    description="Cancel an ingestion job that is in progress.",
)
async def cancel_job(
    job_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: dict = Depends(get_current_user),
) -> IngestionJob:
    """Cancel an ingestion job.

    Args:
        job_id: ID of the ingestion job to cancel
        ingestion_service: Ingestion service instance
        user: Current authenticated user

    Returns:
        IngestionJob with updated status

    Raises:
        HTTPException: If cancelling the job fails
    """
    try:
        logger.info(f"Cancelling job: {job_id}")
        return await ingestion_service.cancel_job(job_id)
    except Exception as e:
        logger.error(f"Failed to cancel job: {e!s}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {e!s}",
        ) from e


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

        # Subscribe to job status updates
        await ingestion_service.subscribe_to_progress(websocket, job_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e!s}")
        # WebSocket connection is likely already closed
        # but try to close it explicitly just in case
        with contextlib.suppress(Exception):
            await websocket.close(code=1011, reason=str(e))
