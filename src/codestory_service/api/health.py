"""API routes for health checks.

This module provides endpoints for checking the health of the service
and its dependencies.
"""

import logging
import time
from typing import Dict, List, Literal, Optional, Union

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from ..infrastructure.neo4j_adapter import Neo4jAdapter, get_neo4j_adapter
from ..infrastructure.celery_adapter import CeleryAdapter, get_celery_adapter
from ..infrastructure.openai_adapter import OpenAIAdapter, get_openai_adapter

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/health", tags=["health"])


class ComponentHealth(BaseModel):
    """Model for component health status."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Health status of the component"
    )
    details: Optional[Dict[str, Union[str, int, float, bool, List[str]]]] = Field(
        None, description="Additional details about the component health"
    )


class HealthReport(BaseModel):
    """Model for service health report."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall health status of the service"
    )
    timestamp: str = Field(
        ..., description="Timestamp of the health check in ISO format"
    )
    version: str = Field(..., description="Service version")
    uptime: int = Field(..., description="Service uptime in seconds")
    components: Dict[str, ComponentHealth] = Field(
        ..., description="Health status of individual components"
    )


# Track service start time
SERVICE_START_TIME = time.time()
SERVICE_VERSION = (
    "0.1.0"  # Would be loaded from package metadata in a real implementation
)


@router.get(
    "",
    response_model=HealthReport,
    summary="Health check",
    description="Check the health of the service and its dependencies.",
)
async def health_check(
    neo4j: Neo4jAdapter = Depends(get_neo4j_adapter),
    celery: CeleryAdapter = Depends(get_celery_adapter),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> HealthReport:
    """Check the health of the service and its dependencies.

    Args:
        neo4j: Neo4j adapter instance
        celery: Celery adapter instance
        openai: OpenAI adapter instance

    Returns:
        HealthReport with health status of the service and its components
    """
    logger.info("Performing health check")

    # Check Neo4j health
    neo4j_health = await neo4j.check_health()

    # Check Celery health
    celery_health = await celery.check_health()

    # Check OpenAI health
    openai_health = await openai.check_health()

    # Calculate service uptime
    uptime = int(time.time() - SERVICE_START_TIME)

    # Determine overall status
    components = {
        "neo4j": ComponentHealth(**neo4j_health),
        "celery": ComponentHealth(**celery_health),
        "openai": ComponentHealth(**openai_health),
    }

    # If any component is unhealthy, the service is unhealthy
    if any(c.status == "unhealthy" for c in components.values()):
        overall_status = "unhealthy"
    # If any component is degraded, the service is degraded
    elif any(c.status == "degraded" for c in components.values()):
        overall_status = "degraded"
    # Otherwise, the service is healthy
    else:
        overall_status = "healthy"

    return HealthReport(
        status=overall_status,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        version=SERVICE_VERSION,
        uptime=uptime,
        components=components,
    )
