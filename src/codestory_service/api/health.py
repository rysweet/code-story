"""API routes for health checks.

This module provides endpoints for checking the health of the service
and its dependencies.
"""
import contextlib
import logging
import os
import time
from typing import Any, Literal, cast
import redis.asyncio as redis
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from ..infrastructure.celery_adapter import CeleryAdapter, get_celery_adapter
from ..infrastructure.error_log import get_and_clear_errors
from ..infrastructure.neo4j_adapter import Neo4jAdapter, get_neo4j_adapter
from ..infrastructure.openai_adapter import OpenAIAdapter, get_openai_adapter
from ..settings import get_service_settings
logger = logging.getLogger(__name__)
router = APIRouter(tags=['health'])

class ComponentHealth(BaseModel):
    """Model for component health status."""
    status: Literal['healthy', 'degraded', 'unhealthy'] = Field(..., description='Health status of the component')
    details: dict[str, Any] | None = Field(None, description='Additional details about the component health')

class HealthReport(BaseModel):
    """Model for service health report."""
    status: Literal['healthy', 'degraded', 'unhealthy'] = Field(..., description='Overall health status of the service')
    timestamp: str = Field(..., description='Timestamp of the health check in ISO format')
    version: str = Field(..., description='Service version')
    uptime: int = Field(..., description='Service uptime in seconds')
    components: dict[str, ComponentHealth] = Field(..., description='Health status of individual components')
    error_package: dict[str, Any] | None = Field(None, description='Package of errors from the service')
SERVICE_START_TIME = time.time()
SERVICE_VERSION = '0.1.0'

@router.get('/health', response_model=HealthReport, summary='Health check', description='Check the health of the service and its dependencies.', status_code=status.HTTP_200_OK)
@router.get('/v1/health', response_model=HealthReport, summary='Health check', description='Check the health of the service and its dependencies.', status_code=status.HTTP_200_OK)
async def health_check(neo4j: Neo4jAdapter=Depends(get_neo4j_adapter), celery: CeleryAdapter=Depends(get_celery_adapter), openai: OpenAIAdapter=Depends(get_openai_adapter), auto_fix: bool=Query(False, description='Automatically attempt to fix Azure authentication issues')) -> HealthReport:
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
    logger.info('=== Health Check Started ===')
    errors = get_and_clear_errors()
    error_package = errors if errors else None
    logger.info(f'Error package: {error_package}')
    try:
        logger.info('Starting health check implementation with 30s timeout...')
        health_report = await asyncio.wait_for(_health_check_impl(neo4j, celery, openai), timeout=30)
        logger.info(f'Health check completed. Overall status: {health_report.status}')
        logger.info(f'Component statuses: {[(name, comp.status) for name, comp in health_report.components.items()]}')
        if error_package:
            health_report.error_package = error_package  # type: ignore[assignment]
            health_report.status = 'unhealthy'
        if auto_fix and health_report.components.get('openai') and (health_report.components['openai'].status == 'unhealthy'):
            logger.info('Auto-fix requested and OpenAI is unhealthy - checking for Azure auth issues...')
            openai_details = health_report.components['openai'].details or {}
            error_str = str(openai_details.get('error', ''))
            error_type = str(openai_details.get('type', ''))
            logger.info(f'OpenAI error details: {openai_details}')
            logger.info(f'Error string: {error_str}')
            logger.info(f'Error type: {error_type}')
            if 'DefaultAzureCredential' in error_str or 'AADSTS700003' in error_str or error_type == 'AuthenticationError':
                logger.info('Azure authentication issue detected, attempting renewal')
                try:
                    renewal_result = await asyncio.wait_for(openai.check_health(), timeout=15)
                    if renewal_result.get('status') == 'healthy':
                        health_report.components['openai'] = ComponentHealth(status='healthy', details={'auth_renewal': True, 'message': 'Azure authentication renewed successfully'})
                        health_report.status = 'healthy'
                except Exception as e:
                    logger.error(f'Azure authentication renewal failed: {e}')
                    if not health_report.components['openai'].details:
                        health_report.components['openai'].details = {}
                    health_report.components['openai'].details['renewal_attempted'] = True
                    health_report.components['openai'].details['renewal_error'] = str(e)
        return health_report
    except TimeoutError:
        logger.error('Health check timed out after 30 seconds')
        return HealthReport(status='degraded', timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), version=SERVICE_VERSION, uptime=int(time.time() - SERVICE_START_TIME), components={'service': ComponentHealth(status='healthy', details={}), 'neo4j': ComponentHealth(status='degraded', details={'error': 'Health check timed out after 30 seconds'}), 'celery': ComponentHealth(status='degraded', details={'error': 'Health check timed out after 30 seconds'}), 'openai': ComponentHealth(status='degraded', details={'error': 'Health check timed out after 30 seconds'}), 'redis': ComponentHealth(status='degraded', details={'error': 'Health check timed out after 30 seconds'})})
    except Exception as e:
        logger.error(f'Unexpected error in health check: {e}')
        return HealthReport(status='unhealthy', timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), version=SERVICE_VERSION, uptime=int(time.time() - SERVICE_START_TIME), components={'service': ComponentHealth(status='unhealthy', details={'error': str(e), 'type': type(e).__name__})})

@router.get('/auth-renew', response_model=dict[str, Any], summary='Renew Azure authentication', description='Attempt to renew Azure authentication tokens.', tags=['health'])
async def auth_renew(openai: OpenAIAdapter=Depends(get_openai_adapter), tenant_id: str | None=Query(None, description='Optional Azure tenant ID for authentication'), inject_into_containers: bool=Query(True, description='Inject tokens into containers after authentication'), restart_containers: bool=Query(False, description='Restart containers after token injection')) -> dict[str, Any]:
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
    logger.info('Azure authentication renewal requested')
    if not tenant_id:
        try:
            env_vars = ['AZURE_TENANT_ID', 'AZURE_OPENAI__TENANT_ID', 'OPENAI__TENANT_ID', 'CODESTORY__OPENAI__TENANT_ID', 'CODESTORY__AZURE__TENANT_ID']
            for env_var in env_vars:
                if os.environ.get(env_var):
                    tenant_id = os.environ[env_var]
                    logger.info(f'Using tenant ID from environment variable {env_var}: {tenant_id}')
                    break
            if not tenant_id:
                from ..settings import get_service_settings
                settings = get_service_settings()
                try:
                    tenant_id = getattr(getattr(settings, 'openai', None), 'tenant_id', None)
                    if tenant_id:
                        logger.info(f'Using tenant ID from service settings (openai): {tenant_id}')
                except Exception:
                    pass
                if not tenant_id:
                    try:
                        from codestory.config.settings import get_settings
                        core_settings = get_settings()
                        tenant_id = getattr(getattr(core_settings, 'openai', None), 'tenant_id', None)
                        if tenant_id:
                            logger.info(f'Using tenant ID from core settings (openai): {tenant_id}')
                        if not tenant_id:
                            tenant_id = getattr(getattr(core_settings, 'azure', None), 'tenant_id', None)
                            if tenant_id:
                                logger.info(f'Using tenant ID from core settings (azure): {tenant_id}')
                    except Exception as e:
                        logger.warning(f'Failed to get tenant ID from core settings: {e}')
            if not tenant_id:
                health_status = await openai.check_health()
                if isinstance(health_status, dict) and health_status.get('status') == 'unhealthy':
                    details = health_status.get('details', {})
                    error_str = str(details.get('error', ''))
                    import re
                    patterns = ["tenant '([0-9a-f-]+)'", 'tenant ID: ([0-9a-f-]+)', "AADSTS500011.+?'([0-9a-f-]+)'", "AADSTS700003.+?'([0-9a-f-]+)'"]
                    for pattern in patterns:
                        tenant_match = re.search(pattern, error_str)
                        if tenant_match:
                            tenant_id = tenant_match.group(1)
                            logger.info(f'Extracted tenant ID from error message: {tenant_id}')
                            break
            if not tenant_id:
                try:
                    import subprocess
                    az_result = subprocess.run(['az', 'account', 'show', '--query', 'tenantId', '-o', 'tsv'], capture_output=True, text=True, timeout=5)
                    if az_result.returncode == 0 and az_result.stdout.strip():
                        tenant_id = az_result.stdout.strip()
                        logger.info(f'Using tenant ID from Azure CLI: {tenant_id}')
                except Exception as e:
                    logger.debug(f'Failed to get tenant ID from Azure CLI: {e}')
        except Exception as e:
            logger.warning(f'Failed to get tenant ID from settings: {e}')
    if tenant_id:
        login_cmd = f'az login --tenant {tenant_id} --scope https://cognitiveservices.azure.com/.default'
    else:
        login_cmd = 'az login --scope https://cognitiveservices.azure.com/.default'
    response = {'status': 'pending', 'message': 'Azure authentication renewal requires manual login', 'login_command': login_cmd, 'instructions': f"Please run '{login_cmd}' in your terminal to authenticate with Azure"}
    if tenant_id:
        response['tenant_id'] = tenant_id
        response['tenant_source'] = 'Found in environment configuration or settings'
        response['auth_message'] = f'Using tenant ID: {tenant_id} from configuration'
        response['auth_details'] = {'tenant_id': tenant_id, 'scope': 'https://cognitiveservices.azure.com/.default', 'browser_login': True, 'auto_inject': inject_into_containers}  # type: ignore[assignment]
    else:
        response['auth_message'] = 'No tenant ID found in configuration, using default login'
    if inject_into_containers:
        try:
            import subprocess
            import sys
            from pathlib import Path
            script_path = Path(__file__).parent.parent.parent.parent / 'scripts' / 'inject_azure_tokens.py'
            if not script_path.exists():
                logger.warning(f'Token injection script not found at {script_path}')
                response['token_injection'] = {'status': 'failed', 'message': 'Token injection script not found'}  # type: ignore[assignment]
            else:
                cmd = [sys.executable, str(script_path)]
                if tenant_id:
                    cmd.extend(['--tenant-id', tenant_id])
                if restart_containers:
                    cmd.append('--restart-containers')
                cmd.append('--verbose')
                logger.info(f"Running token injection command: {' '.join(cmd)}")
                import asyncio
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

                class AsyncSubprocessResult:

                    def __init__(self, returncode: Any, stdout: Any, stderr: Any) -> None:
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr
                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                    injection_result_code = proc.returncode
                    injection_stdout = stdout.decode('utf-8') if stdout else ''
                    injection_stderr = stderr.decode('utf-8') if stderr else ''
                    injection_result = AsyncSubprocessResult(injection_result_code, injection_stdout, injection_stderr)
                    if injection_result.returncode == 0:
                        response['token_injection'] = {'status': 'success', 'message': 'Azure tokens successfully injected into containers', 'restart': 'Containers restarted successfully' if restart_containers else None}  # type: ignore[assignment]
                    else:
                        response['token_injection'] = {'status': 'failed', 'message': 'Failed to inject Azure tokens into containers', 'error': injection_stderr}  # type: ignore[assignment]
                except TimeoutError:
                    if proc.returncode is None:
                        with contextlib.suppress(Exception):
                            proc.terminate()
                    logger.error('Token injection process timed out after 30 seconds')
                    response['token_injection'] = {'status': 'timeout', 'message': 'Token injection process timed out after 30 seconds'}  # type: ignore[assignment]
                except Exception as e:
                    logger.error(f'Error running token injection process: {e}')
                    response['token_injection'] = {'status': 'error', 'message': f'Error running token injection process: {e!s}'}  # type: ignore[assignment]
        except Exception as e:
            logger.error(f'Failed to inject tokens into containers: {e}')
            response['token_injection'] = {'status': 'error', 'message': f'Failed to inject tokens into containers: {e!s}'}  # type: ignore[assignment]
    return response

async def _health_check_impl(neo4j: Neo4jAdapter, celery: CeleryAdapter, openai: OpenAIAdapter) -> HealthReport:
    """Shared implementation for all health check endpoints.

    Args:
        neo4j: Neo4j adapter instance
        celery: Celery adapter instance
        openai: OpenAI adapter instance

    Returns:
        HealthReport with health status of the service and its components
    """
    import asyncio
    logger.info('Performing health check')

    async def check_component_health(component_name, check_func, timeout_seconds=5) -> None:
        try:
            result = await asyncio.wait_for(check_func(), timeout=timeout_seconds)
            return result
        except TimeoutError:
            logger.error(f'{component_name} health check timed out after {timeout_seconds} seconds')
            return {'status': 'unhealthy', 'details': {'error': f'Health check timed out after {timeout_seconds} seconds', 'type': 'TimeoutError'}}
        except Exception as e:
            logger.error(f'{component_name} health check failed with exception: {e}')
            return {'status': 'unhealthy', 'details': {'error': str(e), 'type': type(e).__name__}}
    tasks = [check_component_health('Neo4j', neo4j.check_health, 5), check_component_health('Celery', celery.check_health, 5), check_component_health('OpenAI', openai.check_health, 10)]
    neo4j_health, celery_health, openai_health = await asyncio.gather(*tasks)

    async def check_redis_health() -> None:
        settings = get_service_settings()
        redis_host = getattr(settings, 'redis_host', 'redis')
        redis_port = getattr(settings, 'redis_port', 6379)
        redis_db = getattr(settings, 'redis_db', 0)
        logger.info(f'Attempting to connect to Redis at {redis_host}:{redis_port}/{redis_db}')
        redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True, socket_timeout=2.0)
        try:
            await redis_client.ping()
            info = await redis_client.info(section='server')
            await redis_client.close()
            return {'status': 'healthy', 'details': {'connection': f'redis://{redis_host}:{redis_port}/{redis_db}', 'version': info.get('redis_version', 'unknown'), 'memory': info.get('used_memory_human', 'unknown')}}
        except Exception as e:
            logger.error(f'Redis health check failed with exception: {e}')
            with contextlib.suppress(Exception):
                await redis_client.close()
            return {'status': 'unhealthy', 'details': {'error': str(e), 'type': type(e).__name__}}
    try:
        redis_health = await asyncio.wait_for(check_redis_health(), timeout=5)
    except TimeoutError:
        logger.error('Redis health check timed out')
        redis_health = {'status': 'unhealthy', 'details': {'error': 'Health check timed out after 5 seconds', 'type': 'TimeoutError'}}
    except Exception as e:
        logger.error(f'Redis health check failed: {e}')
        redis_health = {'status': 'unhealthy', 'details': {'error': str(e), 'type': type(e).__name__}}
    uptime = int(time.time() - SERVICE_START_TIME)
    components = {'neo4j': ComponentHealth(**neo4j_health), 'celery': ComponentHealth(**celery_health), 'openai': ComponentHealth(**openai_health), 'redis': ComponentHealth(**redis_health)}  # type: ignore[assignment]
    unhealthy_count = sum((1 for c in components.values() if c.status == 'unhealthy'))
    degraded_count = sum((1 for c in components.values() if c.status == 'degraded'))
    if components['celery'].status == 'unhealthy':
        overall_status = 'unhealthy'
    elif unhealthy_count > 2:
        overall_status = 'unhealthy'
    elif unhealthy_count > 0 or degraded_count > 0:
        overall_status = 'degraded'
    else:
        overall_status = 'healthy'
    overall_status_literal = cast("Literal['healthy', 'degraded', 'unhealthy']", overall_status)
    return HealthReport(status=overall_status_literal, timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), version=SERVICE_VERSION, uptime=uptime, components=components)