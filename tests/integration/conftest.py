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

    container = client.containers.run(
        "redis:7.2-alpine",
        name=container_name,
        ports={"6379/tcp": 6379},
        detach=True,
        auto_remove=True,
    )
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

        url = f"redis://localhost:{port}/0"
        os.environ["REDIS_URL"] = url
        os.environ["CELERY_BROKER_URL"] = url
        os.environ["CELERY_RESULT_BACKEND"] = url
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
