import os
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

from pathlib import Path
import pytest
import tempfile
import os
import json

@pytest.fixture(scope="session", autouse=True)
def force_docker_anonymous_for_tests():
    """
    Session-scoped fixture to force Docker SDK to use a minimal config.json
    with no credential helpers, ensuring integration tests do not fail
    due to missing docker-credential-desktop or other host config issues.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        with open(config_path, "w") as f:
            json.dump({"auths": {}}, f)
        os.environ["DOCKER_CONFIG"] = tmpdir
        print(
            "\n[pytest] Integration tests: Forcing Docker anonymous pulls by setting DOCKER_CONFIG to temp dir with minimal config.json"
        )
        yield
    # No cleanup needed; TemporaryDirectory cleans up automatically.
import uuid
import docker
import docker.errors
import redis
import time
import socket

@pytest.fixture(scope="session", autouse=True)
def redis_container():
    """
    Session-scoped fixture to start a Redis container for integration tests.
    - Uses docker-py to run a Redis 7.2-alpine container with a random name and mapped port.
    - Waits for Redis to be ready.
    - Sets REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND env vars for the test process.
    - Stops the container on teardown.
    """
    client = docker.from_env()
    container_name = f"test-redis-{uuid.uuid4()}"

    # Check if port 6379 is available
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 6379))
        sock.close()
    except OSError:
        pytest.skip("Redis port 6379 in use")

    try:
        container = client.containers.run(
            "redis:7.2-alpine",
            name=container_name,
            ports={"6379/tcp": 6379},
            detach=True,
            auto_remove=True,
        )
    except docker.errors.APIError as e:
        if "port is already allocated" in str(e):
            pytest.skip("Redis port 6379 in use")
        else:
            raise
    try:
        # Find mapped host port
        container.reload()
        port_info = container.attrs["NetworkSettings"]["Ports"]["6379/tcp"][0]
        host = port_info["HostIp"]
        port = int(port_info["HostPort"])

        # Wait for Redis to be ready
        r = redis.Redis(host=host, port=port, db=0)
        for _ in range(30):
            try:
                r.ping()
                break
            except redis.exceptions.ConnectionError:
                time.sleep(0.5)
        else:
            raise RuntimeError("Redis container did not become ready in time")

        import os, importlib, sys
        redis_url = "redis://localhost:6379/0"
        os.environ.update({
            "REDIS_URL": redis_url,
            "CELERY_BROKER_URL": redis_url,
            "CELERY_RESULT_BACKEND": redis_url,
        })

        yield
    finally:
        try:
            container.stop(timeout=3)
        except Exception:
            pass
@pytest.fixture(scope="session", autouse=True)
def celery_worker_container(redis_container):
    """
    Session-scoped fixture to run a real Celery worker in a Docker container for integration tests.
    - Depends on redis_container (ensures Redis is running on host:6379).
    - Uses docker-py to run celery:5.3-alpine with network_mode=host.
    - Waits for worker to connect to Redis (log line) or skips tests on timeout.
    - Stops the container on teardown.
    """
    import docker
    import time
    from uuid import uuid4

    client = docker.from_env()
    container_name = f"cs-worker-{uuid4()}"
    redis_url = "redis://host.docker.internal:6379/0"
    env = {
        "CELERY_BROKER_URL": redis_url,
        "CELERY_RESULT_BACKEND": redis_url,
    }
    command = [
        "celery",
        "-A",
        "codestory.ingestion_pipeline.celery_app",
        "worker",
        "--loglevel=info",
    ]
    try:
        container = client.containers.run(
            "celery:5.3-alpine",
            name=container_name,
            command=command,
            environment=env,
            network_mode="host",
            detach=True,
            auto_remove=True,
        )
    except Exception as e:
        import pytest
        pytest.skip(f"Could not start celery worker container: {e}")

    # Wait for worker to connect to Redis (max 30s)
    log_match = "Connected to redis://localhost:6379/0"
    found = False
    start = time.time()
    try:
        while time.time() - start < 30:
            logs = container.logs(tail=50).decode(errors="ignore")
            if log_match in logs:
                found = True
                break
            time.sleep(1)
        if not found:
            container.stop(timeout=3)
            import pytest
            pytest.skip("Celery worker did not connect to Redis in time")
        yield
    finally:
        try:
            container.stop(timeout=3)
        except Exception:
            pass

_INTEGRATION_ROOT = Path(__file__).parent.resolve()

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    Automatically add the 'integration' marker to all tests collected
    from paths inside tests/integration/. This guarantees they are
    excluded when running `pytest -m "not integration"`.
    """
    for item in items:
        try:
            if Path(item.fspath).resolve().is_relative_to(_INTEGRATION_ROOT):
                item.add_marker(pytest.mark.integration)
        except AttributeError:
            # Python < 3.9 compatibility: fallback manual check
            if str(_INTEGRATION_ROOT) in str(item.fspath):
                item.add_marker(pytest.mark.integration)
