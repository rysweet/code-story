"""API routes for ingestion pipeline operations.

This module provides endpoints for starting, monitoring, and managing
ingestion pipeline jobs.
"""

import contextlib
import logging
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status, Body

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
    description=(
        "Start a new ingestion pipeline job with the specified source and options.\n\n"
        "Scheduling support:\n"
        "- `eta`: Optional datetime (ISO 8601 string or Unix timestamp) at which to schedule the job.\n"
        "- `countdown`: Optional number of seconds to delay job execution from now.\n"
        "If both are provided, `eta` takes precedence."
    ),
)
async def start_ingestion(
    request: IngestionRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: Dict[str, Any] = Depends(get_current_user),
) -> IngestionStarted:
    """Start an ingestion pipeline job.

    Args:
        request: Details of the ingestion request. Supports scheduling via `eta` (datetime or timestamp) or `countdown` (seconds).
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
        logger.info(f"Received ingestion request: {request.model_dump_json()}")
        import os
        # Skip path existence check in test environment
        if os.environ.get("CODESTORY_TEST_ENV") == "true":
            logger.info(f"[TEST MODE] Skipping path existence check for source: {request.source}")
        else:
            logger.info(f"Path exists: {os.path.exists(request.source)} for source: {request.source}")
        logger.info(f"Request fields: source={request.source!r}, source_type={request.source_type!r}, branch={request.branch!r}, steps={request.steps!r}, dependencies={request.dependencies!r}, config={request.config!r}, options={request.options!r}, created_by={request.created_by!r}, description={request.description!r}, tags={request.tags!r}, priority={request.priority!r}, eta={request.eta!r}, countdown={request.countdown!r}")
        logger.info(f"Starting ingestion for source: {request.source}")
        return await ingestion_service.start_ingestion(request)
    except Exception as e:
        import traceback
        logger.error(f"Failed to start ingestion: {e!s}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        if isinstance(e, HTTPException):
            import traceback
            logger.error(f"HTTPException detail: {getattr(e, 'detail', None)}")
            logger.error(f"HTTPException traceback: {traceback.format_exc()}")
            if hasattr(e, "body"):
                logger.error(f"HTTPException body: {e.body}")
            if hasattr(e, "errors"):
                logger.error(f"HTTPException errors: {getattr(e, 'errors', None)}")
            # Print the request object for debugging
            try:
                logger.error(f"Request object at failure: {request.model_dump_json()}")
            except Exception as dump_exc:
                logger.error(f"Failed to dump request object: {dump_exc}")
            # Print the full exception object
            logger.error(f"HTTPException full: {e}")
            # Print the full FastAPI validation error if present
            if hasattr(e, "detail") and isinstance(e.detail, list):
                for err in e.detail:
                    logger.error(f"Validation error: {err}")
            # Print the full request object and all fields
            logger.error(f"Request fields at failure: {request.__dict__}")
            # Print the full request body if available
            if hasattr(request, "body"):
                try:
                    logger.error(f"Request body at failure: {request.body}")
                except Exception as body_exc:
                    logger.error(f"Failed to dump request body: {body_exc}")
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
    job_status: Union[List[JobStatus], None] = Query(
        None, description="Filter by job status"
    ),
    limit: int = Query(10, description="Maximum number of jobs to return"),
    offset: int = Query(0, description="Number of jobs to skip"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort direction (asc or desc)"),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: Dict[str, Any] = Depends(get_current_user),
) -> PaginatedIngestionJobs:
    """List ingestion jobs with optional filtering.

    Args:
        job_status: List of job statuses to filter by
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
        logger.info(f"Listing jobs with status filter: {job_status}")
        return await ingestion_service.list_jobs(
            status=job_status,
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
    user: Dict[str, Any] = Depends(get_current_user),
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
    body: dict = Body(default_factory=dict),  # Accept and ignore any body for compatibility
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: Dict[str, Any] = Depends(get_current_user),
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


@router.get(
    "/resource_status",
    summary="Get resource usage and limits",
    description="Get the current resource token usage and limits for ingestion throttling.",
)
async def get_resource_status(
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get the current resource token usage, limits, and recent job metrics for ingestion.

    Args:
        ingestion_service: Ingestion service instance
        user: Current authenticated user

    Returns:
        Dictionary containing resource status information
    """
    return await ingestion_service.get_resource_status()


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
