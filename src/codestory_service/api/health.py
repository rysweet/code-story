"""API routes for health checks.

This module provides endpoints for checking the health of the service
and its dependencies.
"""

import logging
import re
import subprocess
import time
from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import APIRouter, Depends, Query, status
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
    auto_fix: bool = Query(False, description="Automatically attempt to fix Azure authentication issues"),
) -> HealthReport:
    """Check the health of the service and its dependencies.

    Args:
        neo4j: Neo4j adapter instance
        celery: Celery adapter instance
        openai: OpenAI adapter instance
        auto_fix: If True, attempt to automatically fix Azure auth issues

    Returns:
        HealthReport with health status of the service and its components
    """
    health_report = await _health_check_impl(neo4j, celery, openai)
    
    # Check if there's an Azure authentication issue
    if auto_fix and health_report.components.get("openai") and health_report.components["openai"].status == "unhealthy":
        openai_details = health_report.components["openai"].details or {}
        error_str = str(openai_details.get("error", ""))
        error_type = str(openai_details.get("type", ""))
        
        # Check if this is an Azure auth issue
        if (
            "DefaultAzureCredential" in error_str or 
            "AADSTS700003" in error_str or 
            error_type == "AuthenticationError"
        ):
            logger.info("Azure authentication issue detected, attempting auto-renewal")
            
            # Try to auto-renew Azure authentication
            try:
                # Extract tenant ID if present
                tenant_id = None
                tenant_match = re.search(r"tenant '([0-9a-f-]+)'", error_str)
                if tenant_match:
                    tenant_id = tenant_match.group(1)
                
                # Look for tenant in solution field
                solution = openai_details.get("solution", "")
                tenant_match = re.search(r"--tenant ([0-9a-f-]+)", solution)
                if tenant_match and not tenant_id:
                    tenant_id = tenant_match.group(1)
                
                # Build renewal command using our comprehensive renewal script
                renewal_cmd = ["python", "/app/scripts/azure_auth_renew.py"]
                if tenant_id:
                    renewal_cmd.extend(["--tenant", tenant_id])
                
                # Run the renewal script with proper logging
                logger.info(f"Initiating auto-renewal with command: {' '.join(renewal_cmd)}")
                try:
                    # Execute renewal script and capture output
                    result = subprocess.run(
                        renewal_cmd, 
                        capture_output=True,
                        text=True,
                        timeout=120  # 2 minute timeout
                    )
                    
                    # Check if renewal was successful
                    if result.returncode == 0:
                        logger.info("Azure authentication renewal was successful")
                        renewal_success = True
                    else:
                        logger.error(f"Azure authentication renewal failed with code {result.returncode}")
                        logger.error(f"Stderr: {result.stderr}")
                        renewal_success = False
                    
                    # Add detailed information to health report
                    if "details" not in health_report.components["openai"]:
                        health_report.components["openai"].details = {}
                    
                    health_report.components["openai"].details["renewal_attempted"] = True
                    health_report.components["openai"].details["renewal_success"] = renewal_success
                    health_report.components["openai"].details["renewal_command"] = " ".join(renewal_cmd)
                    
                    # Add output logs only if there was an error
                    if not renewal_success:
                        health_report.components["openai"].details["renewal_stdout"] = result.stdout[:500] if result.stdout else ""
                        health_report.components["openai"].details["renewal_stderr"] = result.stderr[:500] if result.stderr else ""
                
                except subprocess.TimeoutExpired:
                    logger.error("Azure authentication renewal timed out")
                    if "details" not in health_report.components["openai"]:
                        health_report.components["openai"].details = {}
                    health_report.components["openai"].details["renewal_attempted"] = True
                    health_report.components["openai"].details["renewal_success"] = False
                    health_report.components["openai"].details["renewal_error"] = "Renewal process timed out after 120 seconds"
                    
                # Use background process for long-running container token injection
                # This will continue even after the response is sent to the client
                try:
                    background_cmd = ["python", "/app/scripts/azure_auth_renew.py", "--container", "all"]
                    subprocess.Popen(
                        background_cmd, 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    logger.info("Started background process for container token injection")
                except Exception as e:
                    logger.error(f"Failed to start background token injection: {e}")
                
                logger.info(f"Auto-renewal completed with command: {' '.join(renewal_cmd)}")
            except Exception as e:
                logger.error(f"Error attempting auto-renewal: {e}")
                if "details" not in health_report.components["openai"]:
                    health_report.components["openai"].details = {}
                health_report.components["openai"].details["renewal_error"] = str(e)
    
    return health_report


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
