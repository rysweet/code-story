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

@pytest.fixture(scope="session")
def redis_container():
    """
    Session-scoped fixture to start a Redis container for integration tests.
    Returns the mapped Redis port for use by dependent fixtures.
    """
    import socket

    client = docker.from_env()
    container_name = f"test-redis-{uuid.uuid4()}"

    # Find a random free port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    free_port = sock.getsockname()[1]
    sock.close()

    try:
        container = client.containers.run(
            "redis:7.2-alpine",
            name=container_name,
            ports={"6379/tcp": free_port},
            detach=True,
            # auto_remove=True,  # REMOVE auto_remove so we can inspect logs if it fails
        )
    except docker.errors.APIError as e:
        raise RuntimeError(f"Could not start Redis container: {e}")

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

        redis_url = f"redis://localhost:{port}/0"
        os.environ.update({
            "REDIS_URL": redis_url,
            "CELERY_BROKER_URL": redis_url,
            "CELERY_RESULT_BACKEND": redis_url,
        })

        yield port
    finally:
        try:
            container.stop(timeout=3)
        except docker.errors.APIError as e:
            if hasattr(e, "status_code") and e.status_code in (404, 409):
                pass
            else:
                raise
        except Exception:
            pass
        client.close()
@pytest.fixture(scope="session")
def celery_worker_container(redis_container):
    """
    Session-scoped fixture to run a real Celery worker in a Docker container for integration tests.
    Uses bridge networking and the mapped Redis port for cross-platform compatibility.
    """
    import docker
    import time
    from uuid import uuid4
    import platform

    port = redis_container
    # Use host.docker.internal on Mac/Windows, localhost on Linux
    if platform.system() == "Linux":
        redis_host = "localhost"
    else:
        redis_host = "host.docker.internal"
    redis_url = f"redis://{redis_host}:{port}/0"

    client = docker.from_env()
    container_name = f"cs-worker-{uuid4()}"
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
        # Clean up any prior worker containers
        for c in client.containers.list(all=True, filters={"name": container_name}):
            try:
                c.remove(force=True)
            except docker.errors.APIError:
                pass
        container = client.containers.run(
            # Use slim Python 3.12 image and install CodeStory package in-container
            "python:3.12-slim",
            name=container_name,
            command=[
                "bash",
                "-c",
                (
                    "apt-get update && apt-get install -y procps docker.io && "
                    "pip install -e . && pip install docker "
                    "&& "  # once installed, launch celery
                    + " ".join(command)
                ),
            ],
            volumes={
                os.getcwd(): {"bind": "/app", "mode": "rw"},
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            },
            working_dir="/app",
            environment=env,
            detach=True,
            auto_remove=False,  # keep container for explicit stop in teardown
            network_mode="host",  # enable host networking for DNS resolution
        )
    except Exception as e:
        import pytest
        pytest.skip(f"Could not start celery worker container: {e}")

    # Wait for worker to connect to Redis (max 30s)
    log_match = f"Connected to redis://{redis_host}:{port}/0"
    found = False
    start = time.time()
    try:
        print(f"[celery_worker_container] Waiting up to 180s for worker to connect to Redis at {redis_url} (log match: {log_match})")
        while time.time() - start < 180:
            logs = container.logs(tail=50).decode(errors="ignore")
            if log_match in logs:
                print(f"[celery_worker_container] Found log match: {log_match}")
                found = True
                break
            time.sleep(1)
        else:
            print(f"[celery_worker_container] Timeout waiting for worker to connect to Redis. Last logs:\n{container.logs().decode(errors='ignore')}")
        if not found:
            logs = container.logs().decode(errors="ignore")
            print(f"Celery worker logs (connection failure):\n{logs}")
            container.stop(timeout=3)
            import pytest
            pytest.skip("Celery worker did not connect to Redis in time")
        # ----------------------------------------------------------------
        # Yield the **container name** so downstream tests can interact with
        # the running worker (e.g., docker exec …).
        # ----------------------------------------------------------------
        yield container.name
    finally:
        try:
            container.stop(timeout=3)
        except docker.errors.APIError as e:
            if hasattr(e, "status_code") and e.status_code in (404, 409):
                pass
            else:
                raise
        except Exception:
            pass
        client.close()

@pytest.fixture(scope="session")
def service_container(redis_container, celery_worker_container):
    """
    Session-scoped fixture that launches the real CodeStory FastAPI service inside a
    Docker container.  It uses a throw-away Python base image so we avoid shipping a
    custom image to CI, and it connects to the Redis instance started by the
    ``redis_container`` fixture.  The fixture is fully self-contained: it starts all
    required resources and guarantees they are cleaned up in the ``finally`` block.
    """
    import docker
    import os
    import platform
    import requests
    import time
    from uuid import uuid4

    # ------------------------------------------------------------------ networking
    port = redis_container
    redis_host = "localhost" if platform.system() == "Linux" else "host.docker.internal"
    redis_url = f"redis://{redis_host}:{port}/0"

    # ------------------------------------------------------------------ container
    client = docker.from_env()
    name = f"cs-service-{uuid4()}"
    container: "docker.models.containers.Container | None" = None
    try:
        container = client.containers.run(
            "python:3.11-slim",
            name=name,
            command=[
                "bash",
                "-c",
                (
                    "pip install -e . "
                    "&& uvicorn codestory_service.main:app --host 0.0.0.0 --port 8000"
                ),
            ],
            volumes={os.getcwd(): {"bind": "/app", "mode": "rw"}},
            working_dir="/app",
            detach=True,
            auto_remove=False,  # keep container for explicit stop() in finally
            environment={
                "REDIS_URL": redis_url,
                "CELERY_BROKER_URL": redis_url,
                "CELERY_RESULT_BACKEND": redis_url,
            },
        )
        print(f"[tests] Started service container: {name}")

        # ------------------------------------------------------- wait for /health
        url = "http://localhost:8000/health"
        start = time.time()
        while time.time() - start < 60:
            try:
                if requests.get(url, timeout=2).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            logs = container.logs().decode(errors="ignore") if container else ""
            print(f"[tests] Service failed to start, logs:\n{logs}")
            raise RuntimeError("Service container did not become healthy in time")

        yield  # --------------------------- the test(s) using this fixture execute
    finally:
        # -------------------------------------------------------------- tear-down
        if container:
            try:
                container.stop(timeout=3)
            except docker.errors.APIError as e:
                # Ignore “container already stopped/removed” races
                if not (hasattr(e, "status_code") and e.status_code in (404, 409)):
                    raise
            except Exception:
                pass
        client.close()
# ------------------------------------------------------------------------------- end service_container

# --- End of all fixtures ---

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
