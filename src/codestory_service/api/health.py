"""API routes for health checks.

This module provides endpoints for checking the health of the service
and its dependencies.
"""

import logging
import os
import time
from typing import Any, Literal, cast

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from ..infrastructure.celery_adapter import CeleryAdapter, get_celery_adapter
from ..infrastructure.neo4j_adapter import Neo4jAdapter, get_neo4j_adapter
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
    details: dict[str, Any] | None = Field(
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
    components: dict[str, ComponentHealth] = Field(
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
    auto_fix: bool = Query(
        False, description="Automatically attempt to fix Azure authentication issues"
    ),
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
    import asyncio

    logger.info("Performing health check")

    # Use a global timeout to prevent the health check from hanging
    try:
        # Run the full health check with a reasonable timeout
        health_report = await asyncio.wait_for(
            _health_check_impl(neo4j, celery, openai),
            timeout=30,  # 30 second timeout for entire health check
        )

        # Handle Azure auth renewal if requested
        if (
            auto_fix
            and health_report.components.get("openai")
            and health_report.components["openai"].status == "unhealthy"
        ):
            openai_details = health_report.components["openai"].details or {}
            error_str = str(openai_details.get("error", ""))
            error_type = str(openai_details.get("type", ""))

            # Check if this is an Azure auth issue
            if (
                "DefaultAzureCredential" in error_str
                or "AADSTS700003" in error_str
                or error_type == "AuthenticationError"
            ):
                logger.info("Azure authentication issue detected, attempting renewal")

                # Try an auth renewal with a timeout
                try:
                    # This will leverage the retry logic in the OpenAI adapter
                    renewal_result = await asyncio.wait_for(
                        openai.check_health(),
                        timeout=15,  # 15 second timeout for renewal attempt
                    )

                    # Check if renewal succeeded
                    if renewal_result.get("status") == "healthy":
                        health_report.components["openai"] = ComponentHealth(
                            status="healthy",
                            details={
                                "auth_renewal": True,
                                "message": "Azure authentication renewed successfully",
                            },
                        )
                        # Update overall health status
                        health_report.status = "healthy"
                except Exception as e:
                    logger.error(f"Azure authentication renewal failed: {e}")
                    # Update the health report with renewal attempt information
                    if not health_report.components["openai"].details:
                        health_report.components["openai"].details = {}
                    health_report.components["openai"].details[
                        "renewal_attempted"
                    ] = True
                    health_report.components["openai"].details["renewal_error"] = str(e)

        return health_report

    except TimeoutError:
        # Return a degraded status if health check times out
        logger.error("Health check timed out after 30 seconds")
        return HealthReport(
            status="degraded",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            version=SERVICE_VERSION,
            uptime=int(time.time() - SERVICE_START_TIME),
            components={
                "service": ComponentHealth(status="healthy", details={}),
                "neo4j": ComponentHealth(
                    status="degraded",
                    details={"error": "Health check timed out after 30 seconds"},
                ),
                "celery": ComponentHealth(
                    status="degraded",
                    details={"error": "Health check timed out after 30 seconds"},
                ),
                "openai": ComponentHealth(
                    status="degraded",
                    details={"error": "Health check timed out after 30 seconds"},
                ),
                "redis": ComponentHealth(
                    status="degraded",
                    details={"error": "Health check timed out after 30 seconds"},
                ),
            },
        )
    except Exception as e:
        # Return an unhealthy status if health check fails unexpectedly
        logger.error(f"Unexpected error in health check: {e}")
        return HealthReport(
            status="unhealthy",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            version=SERVICE_VERSION,
            uptime=int(time.time() - SERVICE_START_TIME),
            components={
                "service": ComponentHealth(
                    status="unhealthy",
                    details={"error": str(e), "type": type(e).__name__},
                ),
            },
        )


@router.get(
    "/auth-renew",
    response_model=dict[str, Any],
    summary="Renew Azure authentication",
    description="Attempt to renew Azure authentication tokens.",
    tags=["health"],
)
async def auth_renew(
    openai: OpenAIAdapter = Depends(get_openai_adapter),
    tenant_id: str
    | None = Query(None, description="Optional Azure tenant ID for authentication"),
    inject_into_containers: bool = Query(
        True, description="Inject tokens into containers after authentication"
    ),
    restart_containers: bool = Query(
        False, description="Restart containers after token injection"
    ),
) -> dict[str, Any]:
    """Renew Azure authentication tokens.

    This endpoint will attempt to renew the Azure authentication tokens used by the service.
    It will:
    1. Check for expired Azure credentials
    2. Provide the command for Azure CLI login that the user should run in their browser
    3. Optionally inject tokens into containers after successful authentication
    4. Optionally restart containers to use the new tokens
    5. Return the updated status

    Args:
        openai: OpenAI adapter instance
        tenant_id: Optional Azure tenant ID to use for authentication
        inject_into_containers: If True, inject tokens into containers after authentication
        restart_containers: If True, restart containers after token injection

    Returns:
        Dictionary with auth renewal status
    """
    import asyncio

    logger.info("Azure authentication renewal requested")

    # Get tenant ID from environment variables if not provided
    if not tenant_id:
        try:
            # Try to get tenant ID from multiple environment sources
            # Azure tenant ID env vars should be checked in this order:
            env_vars = [
                "AZURE_TENANT_ID",
                "AZURE_OPENAI__TENANT_ID",
                "OPENAI__TENANT_ID",
                "CODESTORY__OPENAI__TENANT_ID",
                "CODESTORY__AZURE__TENANT_ID",
            ]

            for env_var in env_vars:
                if os.environ.get(env_var):
                    tenant_id = os.environ[env_var]
                    logger.info(
                        f"Using tenant ID from environment variable {env_var}: {tenant_id}"
                    )
                    break

            # If not found in env vars, try to get from settings
            if not tenant_id:
                # First try service settings
                from ..settings import get_service_settings

                settings = get_service_settings()

                # Try to get tenant ID from OpenAI settings
                try:
                    tenant_id = getattr(
                        getattr(settings, "openai", None), "tenant_id", None
                    )
                    if tenant_id:
                        logger.info(
                            f"Using tenant ID from service settings (openai): {tenant_id}"
                        )
                except Exception:
                    pass

                # If still not found, try to get from core settings
                if not tenant_id:
                    try:
                        from codestory.config.settings import get_settings

                        core_settings = get_settings()
                        tenant_id = getattr(
                            getattr(core_settings, "openai", None), "tenant_id", None
                        )
                        if tenant_id:
                            logger.info(
                                f"Using tenant ID from core settings (openai): {tenant_id}"
                            )

                        # Try Azure settings if OpenAI settings don't have it
                        if not tenant_id:
                            tenant_id = getattr(
                                getattr(core_settings, "azure", None), "tenant_id", None
                            )
                            if tenant_id:
                                logger.info(
                                    f"Using tenant ID from core settings (azure): {tenant_id}"
                                )
                    except Exception as e:
                        logger.warning(
                            f"Failed to get tenant ID from core settings: {e}"
                        )

            # If still not found, try to extract from Azure error message
            if not tenant_id:
                health_status = await openai.check_health()
                if (
                    isinstance(health_status, dict)
                    and health_status.get("status") == "unhealthy"
                ):
                    details = health_status.get("details", {})
                    error_str = str(details.get("error", ""))

                    # Try to extract tenant ID from error message
                    import re

                    # Try different patterns that might appear in error messages
                    patterns = [
                        r"tenant '([0-9a-f-]+)'",
                        r"tenant ID: ([0-9a-f-]+)",
                        r"AADSTS500011.+?'([0-9a-f-]+)'",
                        r"AADSTS700003.+?'([0-9a-f-]+)'",
                    ]

                    for pattern in patterns:
                        tenant_match = re.search(pattern, error_str)
                        if tenant_match:
                            tenant_id = tenant_match.group(1)
                            logger.info(
                                f"Extracted tenant ID from error message: {tenant_id}"
                            )
                            break

            # If still not found, try Azure CLI
            if not tenant_id:
                try:
                    import subprocess

                    # Try to get tenant ID from current Azure account
                    az_result = subprocess.run(
                        ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5,
                    )
                    if az_result.returncode == 0 and az_result.stdout.strip():
                        tenant_id = az_result.stdout.strip()
                        logger.info(f"Using tenant ID from Azure CLI: {tenant_id}")
                except Exception as e:
                    logger.debug(f"Failed to get tenant ID from Azure CLI: {e}")

        except Exception as e:
            logger.warning(f"Failed to get tenant ID from settings: {e}")

    # Construct the login command for display
    if tenant_id:
        login_cmd = f"az login --tenant {tenant_id} --scope https://cognitiveservices.azure.com/.default"
    else:
        login_cmd = "az login --scope https://cognitiveservices.azure.com/.default"

    # Build the response dict (do not reuse 'result' for subprocess results)
    response = {
        "status": "pending",
        "message": "Azure authentication renewal requires manual login",
        "login_command": login_cmd,
        "instructions": f"Please run '{login_cmd}' in your terminal to authenticate with Azure",
    }

    if tenant_id:
        response["tenant_id"] = tenant_id
        response["tenant_source"] = "Found in environment configuration or settings"
        response["auth_message"] = f"Using tenant ID: {tenant_id} from configuration"
        response["auth_details"] = {
            "tenant_id": tenant_id,
            "scope": "https://cognitiveservices.azure.com/.default",
            "browser_login": True,
            "auto_inject": inject_into_containers,
        }
    else:
        response[
            "auth_message"
        ] = "No tenant ID found in configuration, using default login"

    # Check if tokens need to be injected into containers
    if inject_into_containers:
        try:
            # Run the token injection script
            import subprocess
            import sys
            from pathlib import Path

            # Find the script path relative to the current file
            script_path = (
                Path(__file__).parent.parent.parent.parent
                / "scripts"
                / "inject_azure_tokens.py"
            )

            if not script_path.exists():
                logger.warning(f"Token injection script not found at {script_path}")
                response["token_injection"] = {
                    "status": "failed",
                    "message": "Token injection script not found",
                }  # type: ignore
            else:
                # Build the command
                cmd = [sys.executable, str(script_path)]
                # Add tenant ID if available
                if tenant_id:
                    cmd.extend(["--tenant-id", tenant_id])
                # Add restart flag if requested
                if restart_containers:
                    cmd.append("--restart-containers")
                # Add verbose flag for debugging
                cmd.append("--verbose")
                logger.info(f"Running token injection command: {' '.join(cmd)}")
                # Run the script and capture output
                import asyncio

                # Create a subprocess with asyncio
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Wait for process to complete with timeout
                class AsyncSubprocessResult:
                    def __init__(self, returncode, stdout, stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr

                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=30
                    )
                    injection_result_code = proc.returncode
                    injection_stdout = stdout.decode("utf-8") if stdout else ""
                    injection_stderr = stderr.decode("utf-8") if stderr else ""
                    injection_result = AsyncSubprocessResult(
                        injection_result_code, injection_stdout, injection_stderr
                    )
                    if injection_result.returncode == 0:
                        response["token_injection"] = {
                            "status": "success",
                            "message": "Azure tokens successfully injected into containers",
                            "restart": "Containers restarted successfully"
                            if restart_containers
                            else None,
                        }
                    else:
                        response["token_injection"] = {
                            "status": "failed",
                            "message": "Failed to inject Azure tokens into containers",
                            "error": injection_stderr,
                        }
                except TimeoutError:
                    if proc.returncode is None:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
                    logger.error("Token injection process timed out after 30 seconds")
                    response["token_injection"] = {
                        "status": "timeout",
                        "message": "Token injection process timed out after 30 seconds",
                    }
                except Exception as e:
                    logger.error(f"Error running token injection process: {e}")
                    response["token_injection"] = {
                        "status": "error",
                        "message": f"Error running token injection process: {e!s}",
                    }
        except Exception as e:
            logger.error(f"Failed to inject tokens into containers: {e}")
            response["token_injection"] = {
                "status": "error",
                "message": f"Failed to inject tokens into containers: {e!s}",
            }  # type: ignore

    # Return response dict
    return response


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
    import asyncio

    logger.info("Performing health check")

    # Define component health check with timeout
    async def check_component_health(component_name, check_func, timeout_seconds=5):
        try:
            # Use asyncio.wait_for to apply timeout to each health check
            result = await asyncio.wait_for(check_func(), timeout=timeout_seconds)
            return result
        except TimeoutError:
            logger.error(
                f"{component_name} health check timed out after {timeout_seconds} seconds"
            )
            return {
                "status": "unhealthy",
                "details": {
                    "error": f"Health check timed out after {timeout_seconds} seconds",
                    "type": "TimeoutError",
                },
            }
        except Exception as e:
            logger.error(f"{component_name} health check failed with exception: {e}")
            return {
                "status": "unhealthy",
                "details": {"error": str(e), "type": type(e).__name__},
            }

    # Run all health checks in parallel with timeouts
    tasks = [
        check_component_health("Neo4j", neo4j.check_health, 5),
        check_component_health("Celery", celery.check_health, 5),
        check_component_health(
            "OpenAI", openai.check_health, 10
        ),  # Longer timeout for OpenAI due to az login calls
    ]

    # Run component checks in parallel
    neo4j_health, celery_health, openai_health = await asyncio.gather(*tasks)

    # Check Redis health with timeout
    async def check_redis_health():
        settings = get_service_settings()
        redis_host = getattr(settings, "redis_host", "redis")
        redis_port = getattr(settings, "redis_port", 6379)
        redis_db = getattr(settings, "redis_db", 0)

        # Log Redis connection details for debugging
        logger.info(
            f"Attempting to connect to Redis at {redis_host}:{redis_port}/{redis_db}"
        )

        # Create Redis client with socket timeout
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_timeout=2.0,  # 2 second socket timeout
        )

        try:
            # Ping Redis to check connection
            await redis_client.ping()

            # Get basic Redis info
            info = await redis_client.info(section="server")

            # Close the connection
            await redis_client.close()

            return {
                "status": "healthy",
                "details": {
                    "connection": f"redis://{redis_host}:{redis_port}/{redis_db}",
                    "version": info.get("redis_version", "unknown"),
                    "memory": info.get("used_memory_human", "unknown"),
                },
            }
        except Exception as e:
            logger.error(f"Redis health check failed with exception: {e}")
            # Make sure to close the Redis connection on error
            try:
                await redis_client.close()
            except:
                pass
            return {
                "status": "unhealthy",
                "details": {"error": str(e), "type": type(e).__name__},
            }

    # Run Redis health check with timeout
    try:
        redis_health = await asyncio.wait_for(check_redis_health(), timeout=5)
    except TimeoutError:
        logger.error("Redis health check timed out")
        redis_health = {
            "status": "unhealthy",
            "details": {
                "error": "Health check timed out after 5 seconds",
                "type": "TimeoutError",
            },
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
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

    # Determine overall status - prioritize service functionality over absolute health
    # Service can be "healthy" for API consumers even with some component issues
    if components["celery"].status == "unhealthy":
        # Celery is a required component for ingestion jobs
        overall_status = "unhealthy"
    elif unhealthy_count > 2:
        # More than half of components unhealthy
        overall_status = "unhealthy"
    elif unhealthy_count > 0 or degraded_count > 0:
        # Some components have issues but service can still function
        overall_status = "degraded"
    else:
        # All components are healthy
        overall_status = "healthy"

    # Ensure overall_status is a valid literal
    overall_status_literal = cast(
        "Literal['healthy', 'degraded', 'unhealthy']", overall_status
    )

    return HealthReport(
        status=overall_status_literal,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        version=SERVICE_VERSION,
        uptime=uptime,
        components=components,
    )
