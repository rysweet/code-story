"""API routes for health checks.

This module provides endpoints for checking the health of the service
and its dependencies.
"""

import logging
import time
from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
import redis.asyncio as redis

from ..infrastructure.neo4j_adapter import Neo4jAdapter, get_neo4j_adapter
from ..infrastructure.celery_adapter import CeleryAdapter, get_celery_adapter
from ..infrastructure.openai_adapter import OpenAIAdapter, get_openai_adapter
from ..settings import get_service_settings

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["health"])


class ComponentHealth(BaseModel):
    """Model for component health status."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Health status of the component"
    )
    details: Optional[Dict[str, Any]] = Field(
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
    "/health",
    response_model=HealthReport,
    summary="Health check",
    description="Check the health of the service and its dependencies.",
    status_code=status.HTTP_200_OK,  # Always return 200 for health endpoint
)
@router.get(
    "/v1/health",
    response_model=HealthReport,
    summary="Health check",
    description="Check the health of the service and its dependencies.",
    status_code=status.HTTP_200_OK,  # Always return 200 for health endpoint
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
    return await _health_check_impl(neo4j, celery, openai)


async def _health_check_impl(
    neo4j: Neo4jAdapter,
    celery: CeleryAdapter,
    openai: OpenAIAdapter,
) -> HealthReport:
    """Shared implementation for all health check endpoints.

    Args:
        neo4j: Neo4j adapter instance
        celery: Celery adapter instance
        openai: OpenAI adapter instance

    Returns:
        HealthReport with health status of the service and its components
    """
    logger.info("Performing health check")

    try:
        # Check Neo4j health
        neo4j_health = await neo4j.check_health()
    except Exception as e:
        logger.error(f"Neo4j health check failed with exception: {e}")
        neo4j_health = {
            "status": "unhealthy",
            "details": {"error": str(e), "type": type(e).__name__},
        }

    try:
        # Check Celery health
        celery_health = await celery.check_health()
    except Exception as e:
        logger.error(f"Celery health check failed with exception: {e}")
        celery_health = {
            "status": "unhealthy",
            "details": {"error": str(e), "type": type(e).__name__},
        }

    try:
        # Check OpenAI health
        openai_health = await openai.check_health()
    except Exception as e:
        logger.error(f"OpenAI health check failed with exception: {e}")
        openai_health = {
            "status": "unhealthy",
            "details": {"error": str(e), "type": type(e).__name__},
        }
        
    # Check Redis health
    try:
        settings = get_service_settings()
        redis_host = getattr(settings, "redis_host", "redis")
        redis_port = getattr(settings, "redis_port", 6379)
        redis_db = getattr(settings, "redis_db", 0)
        
        # Log Redis connection details for debugging
        logger.info(f"Attempting to connect to Redis at {redis_host}:{redis_port}/{redis_db}")
        
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        
        # Ping Redis to check connection
        await redis_client.ping()
        
        # Get some Redis info
        info = await redis_client.info()
        
        # Close the connection
        await redis_client.close()
        
        redis_health = {
            "status": "healthy",
            "details": {
                "connection": f"redis://{redis_host}:{redis_port}/{redis_db}",
                "version": info.get("redis_version", "unknown"),
                "memory": info.get("used_memory_human", "unknown")
            }
        }
    except Exception as e:
        logger.error(f"Redis health check failed with exception: {e}")
        redis_health = {
            "status": "unhealthy",
            "details": {"error": str(e), "type": type(e).__name__},
        }

    # Calculate service uptime
    uptime = int(time.time() - SERVICE_START_TIME)

    # Determine overall status
    components = {
        "neo4j": ComponentHealth(**neo4j_health),
        "celery": ComponentHealth(**celery_health),
        "openai": ComponentHealth(**openai_health),
        "redis": ComponentHealth(**redis_health),
    }

    # Check component statuses
    unhealthy_count = sum(1 for c in components.values() if c.status == "unhealthy")
    degraded_count = sum(1 for c in components.values() if c.status == "degraded")
    
    # Determine overall status
    # Celery is a required component - if it's unhealthy, the service is unhealthy
    if components["celery"].status == "unhealthy":
        overall_status = "unhealthy"
    elif unhealthy_count > 0:
        # Any unhealthy component makes the service unhealthy
        overall_status = "unhealthy"
    elif degraded_count > 0:
        # Some components are degraded
        overall_status = "degraded"
    else:
        # All components are healthy
        overall_status = "healthy"

    return HealthReport(
        status=overall_status,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        version=SERVICE_VERSION,
        uptime=uptime,
        components=components,
    )
