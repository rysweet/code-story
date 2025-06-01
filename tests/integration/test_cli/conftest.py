"""Test fixtures for CLI integration tests."""
import os
import subprocess
import tempfile
import time
from collections.abc import Generator
from typing import Any
import httpx
import pytest
from click.testing import CliRunner
from codestory.config import get_settings

@pytest.fixture
def cli_runner() -> CliRunner:
    """
    Creates a Click CLI test runner.

    Returns:
        Click CLI test runner.
    """
    return CliRunner()

def pytest_configure(config: Any) -> None:
    """Add custom markers to pytest."""
    config.addinivalue_line('markers', 'require_service: mark test as requiring a running Code Story service')

@pytest.fixture(scope='session')
def running_service(request: Any) -> Generator[dict[str, Any], None, None]:
    """
    Ensures the Code Story service is running for integration tests.

    If the service is already running, uses the existing instance.
    Otherwise, starts the service automatically.

    Yields:
        Dictionary with service information (url, port, etc.)
    """
    import os
    import signal
    settings = get_settings()
    service_url = f'http://localhost:{settings.service.port}'
    health_url = f'{service_url}/v1/health'
    service_running = False
    service_process = None
    try:
        response = httpx.get(f'{health_url}', timeout=2.0)
        if response.status_code == 200:
            service_running = True
            print('Service is already running, using existing instance')
    except httpx.RequestError:
        pass
    if not service_running:
        print('Starting Code Story service for integration tests...')
        try:
            print('Attempting to use CLI service management...')
            subprocess.run(['python', '-m', 'codestory.cli.main', 'service', 'start'], check=True, timeout=10)
            time.sleep(2)
            try:
                response = httpx.get(f'{health_url}', timeout=2.0)
                if response.status_code == 200:
                    service_running = True
                    print('Service started successfully using CLI!')
            except httpx.RequestError:
                pass
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            print(f'CLI service start failed: {e}')
        if not service_running:
            print('Trying direct service start approach...')
            try:
                subprocess.run(['docker-compose', 'up', '-d', 'neo4j'], check=True, capture_output=True, timeout=30)
                print('Started Neo4j container')
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f'Warning: Failed to start Neo4j container: {e}')
            time.sleep(5)
            print('Starting service process...')
            try:
                service_process = subprocess.Popen(['python', '-m', 'codestory.service', 'start'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
            except Exception as e:
                print(f'Failed to start service process: {e}')
                try:
                    print('Trying alternative service start...')
                    service_process = subprocess.Popen(['python', '-m', 'codestory.cli.main', 'service', 'start', '--debug'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
                except Exception as e:
                    print(f'Failed to start service with alternative approach: {e}')
            started = False
            for i in range(45):
                time.sleep(1)
                print(f'Waiting for service to start (attempt {i + 1}/45)...')
                try:
                    response = httpx.get(f'{health_url}', timeout=2.0)
                    if response.status_code == 200:
                        started = True
                        print('Service started successfully!')
                        break
                except httpx.RequestError:
                    pass
            if not started:
                print('Service failed to start in time')
                try:
                    print('--- Neo4j logs ---')
                    subprocess.run(['docker', 'logs', 'codestory-neo4j-test'], check=False)
                except Exception as e:
                    print(f'Could not get Neo4j logs: {e}')
                try:
                    print('--- Service logs ---')
                    subprocess.run(['docker', 'logs', 'codestory-service'], check=False)
                except Exception as e:
                    print(f'Could not get service logs: {e}')
                if service_process:
                    print('Terminating service process...')
                    try:
                        if service_process.poll() is None:
                            os.killpg(os.getpgid(service_process.pid), signal.SIGTERM)
                    except (ProcessLookupError, OSError) as e:
                        print(f'Process already terminated: {e}')
                try:
                    response = httpx.get(f'{health_url}', timeout=2.0)
                    if response.status_code == 200:
                        service_running = True
                        print('Service is available despite startup issues!')
                        return
                except httpx.RequestError:
                    pass
                raise Exception('Failed to start Code Story service after multiple attempts')
            redis_healthy = False
            for i in range(30):
                try:
                    result = subprocess.run(['docker', 'inspect', '-f', '{{.State.Health.Status}}', 'codestory-redis-test'], capture_output=True, text=True, timeout=3)
                    if result.stdout.strip() == 'healthy':
                        redis_healthy = True
                        print('Redis container is healthy.')
                        break
                    else:
                        print(f'Waiting for Redis to be healthy (attempt {i + 1}/30)... Status: {result.stdout.strip()}')
                except Exception as e:
                    print(f'Error checking Redis health: {e}')
                time.sleep(1)
            if not redis_healthy:
                print('Redis container did not become healthy in time.')
    print(f'Service available at {service_url}')
    yield {'url': service_url, 'port': settings.service.port, 'api_url': f'{service_url}/v1'}
    if service_process:
        print('Stopping Code Story service...')
        try:
            if service_process.poll() is None:
                os.killpg(os.getpgid(service_process.pid), signal.SIGTERM)
        except (ProcessLookupError, OSError) as e:
            print(f'Process already terminated: {e}')
        try:
            subprocess.run(['docker-compose', 'stop'], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f'Warning: Failed to stop services: {e}')

@pytest.fixture
def test_repository() -> Generator[str, None, None]:
    """
    Creates a temporary test repository for ingestion tests.

    Yields:
        Path to the temporary repository.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        os.makedirs(os.path.join(temp_dir, 'src'))
        os.makedirs(os.path.join(temp_dir, 'docs'))
        with open(os.path.join(temp_dir, 'src', 'main.py'), 'w') as f:
            f.write('\ndef main():\n    print("Hello world!")\n\nif __name__ == "__main__":\n    main()\n')
        with open(os.path.join(temp_dir, 'src', 'utils.py'), 'w') as f:
            f.write('\ndef helper_function():\n    return "Helper function"\n')
        with open(os.path.join(temp_dir, 'docs', 'README.md'), 'w') as f:
            f.write('\n# Test Repository\n\nThis is a test repository for Code Story CLI integration tests.\n')
        yield temp_dir