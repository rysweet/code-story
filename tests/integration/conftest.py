import os

# Use compose-mapped ports for integration tests by default
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6380/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6380/0")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7688")
os.environ.setdefault("NEO4J_HTTP_URL", "http://localhost:7475")

import contextlib
import socket

def _find_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

from pathlib import Path
import pytest
import tempfile
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
    Session-scoped fixture to start a Redis container for integration tests on a user-defined bridge network.
    Returns the container name for use by dependent fixtures.
    """
    import docker

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
        )
    except docker.errors.APIError as e:
        raise RuntimeError(f"Could not start Redis container: {e}")

    try:
        # Wait for Redis to be ready
        r = redis.Redis(host="localhost", port=free_port, db=0)
        for _ in range(30):
            try:
                r.ping()
                break
            except redis.exceptions.ConnectionError:
                time.sleep(0.5)
        else:
            raise RuntimeError("Redis container did not become ready in time")

        redis_url = f"redis://localhost:{free_port}/0"
        os.environ.update({
            "REDIS_URL": redis_url,
            "CELERY_BROKER_URL": redis_url,
            "CELERY_RESULT_BACKEND": redis_url,
        })

        yield free_port
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
def neo4j_container():
    """
    Session-scoped fixture to start a Neo4j container for integration tests.
    Always uses random free ports for bolt and http to avoid collisions.
    Sets required env, waits for bolt, and cleans up.
    """
    import docker
    import time
    import platform
    import uuid
    import json
    import os

    client = docker.from_env()
    container_name = f"test-neo4j-{uuid.uuid4()}"

    # Always use random free ports for bolt and http
    bolt_port, http_port = _find_free_port(), _find_free_port()
    print(f"[neo4j_container] Using bolt={bolt_port}, http={http_port}")

    image = "neo4j:5.18.0-enterprise"

    env = {
        "NEO4J_AUTH": "neo4j/password",
        "NEO4J_ACCEPT_LICENSE_AGREEMENT": "yes",
        "NEO4J_PLUGINS": json.dumps(["apoc", "graph-data-science"]),
        "NEO4J_dbms_security_procedures_unrestricted": "apoc.*,gds.*",
        "NEO4J_dbms_connector_bolt_advertised__address": f"localhost:{bolt_port}",
        "NEO4J_dbms_connector_http_advertised__address": f"localhost:{http_port}",
    }

    ports = {
        "7687/tcp": bolt_port,
        "7474/tcp": http_port,
    }

    try:
        container = client.containers.run(
            image,
            name=container_name,
            ports=ports,
            environment=env,
            detach=True,
        )
        # Store Docker DNS name for downstream fixtures
        neo4j_host_dns = container.name  # Docker bridge DNS
        os.environ["NEO4J_HOST_DNS"] = neo4j_host_dns
    except docker.errors.APIError as e:
        client.close()
        raise RuntimeError(f"Could not start Neo4j container: {e}")

    try:
        # Wait for bolt port to be ready (max 90s)
        start = time.time()
        while time.time() - start < 90:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.settimeout(1)
                s.connect(("localhost", bolt_port))
                s.close()
                break
            except Exception:
                time.sleep(1)
            finally:
                s.close()
        else:
            logs = container.logs().decode(errors="ignore")
            print(f"[neo4j_container] Neo4j did not become ready in time. Logs:\n{logs}")
            container.stop(timeout=3)
            client.close()
            raise RuntimeError("Neo4j container did not become ready in time")

        # Set environment variables for other fixtures/tests
        os.environ.update({
            "NEO4J_URI": f"bolt://localhost:{bolt_port}",
            "NEO4J_HTTP_URL": f"http://localhost:{http_port}",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "password",
        })

        yield  # No need to yield ports; service_container will use env values
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
    Uses the mapped host port for Redis. Builds the worker image once per session for fast startup.
    """
    import docker
    import time
    from uuid import uuid4
    import platform
    import pathlib

    port = redis_container
    # Use host.docker.internal on Mac/Windows, localhost on Linux
    if platform.system() == "Linux":
        redis_host = "localhost"
    else:
        redis_host = "host.docker.internal"
    redis_url = f"redis://{redis_host}:{port}/0"

    client = docker.from_env()
    container_name = f"cs-worker-{uuid4()}"
    image_tag = "codestory-celery-worker:test"
    project_root = pathlib.Path(__file__).resolve().parents[1]

    # Build the worker image once per session if not present
    try:
        client.images.get(image_tag)
    except docker.errors.ImageNotFound:
        print(f"[celery_worker_container] Building worker image {image_tag} ...")
        try:
            client.images.remove(image=image_tag, force=True)
        except docker.errors.ImageNotFound:
            pass
        client.images.build(
            path=str(project_root.parent),
            dockerfile="Dockerfile.worker",
            tag=image_tag,
            rm=True,
            pull=True,
            nocache=True,
        )

    env = {
        "CELERY_BROKER_URL": redis_url,
        "CELERY_RESULT_BACKEND": redis_url,
    }
    command = [
        "bash",
        "-c",
        (
            "python -m venv /tmp/venv && "
            ". /tmp/venv/bin/activate && "
            "export PIP_DEFAULT_TIMEOUT=120 && "
            "/tmp/venv/bin/pip install --retries 20 --progress-bar off --no-cache-dir "
            "wheel celery docker azure-identity && "
            "/tmp/venv/bin/pip install --retries 20 --progress-bar off --no-cache-dir -e . && "
            "celery -A codestory.ingestion_pipeline.celery_app worker "
            "--loglevel=info --concurrency=4 -Q ingestion"
        ),
    ]
    try:
        # Clean up any prior worker containers
        for c in client.containers.list(all=True, filters={"name": container_name}):
            try:
                c.remove(force=True)
            except docker.errors.APIError:
                pass
        container = client.containers.run(
            image_tag,
            name=container_name,
            command=command,
            volumes={
                os.getcwd(): {"bind": "/app", "mode": "rw"},
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            },
            working_dir="/app",
            environment=env,
            detach=True,
            auto_remove=False,
        )
    except Exception as e:
        import pytest
        pytest.fail(f"Could not start celery worker container: {e}")

    # Wait for worker to connect to Redis (max 180s)
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
            pytest.fail("Celery worker did not connect to Redis in time")
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
        
        try:
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
        
        client.close()

@pytest.fixture(scope="session")
def service_container(redis_container, celery_worker_container, neo4j_container):
    """
    Session-scoped fixture that launches the real CodeStory FastAPI service inside a
    Docker container. Uses the Redis and Neo4j containers started by the other fixtures.
    Reads Neo4j ports from environment variables set by neo4j_container.
    """
    import docker
    import os
    import platform
    import requests
    import time
    from uuid import uuid4

    # ------------------------------------------------------------------ networking
    redis_port = redis_container
    redis_host = "localhost" if platform.system() == "Linux" else "host.docker.internal"
    redis_url = f"redis://{redis_host}:{redis_port}/0"

    # Find a free port for the service
    service_port = _find_free_port()

    # Neo4j ports from env
    # Use Neo4j container's Docker DNS name and default internal ports
    neo4j_host = os.getenv("NEO4J_HOST_DNS")
    bolt_port = 7687  # inside network (container's default)
    http_port = 7474
    neo4j_uri = f"bolt://{neo4j_host}:{bolt_port}"
    neo4j_http_url = f"http://{neo4j_host}:{http_port}"

    # ------------------------------------------------------------------ container
    client = docker.from_env()
    name = f"cs-service-{uuid4()}"
    container: "docker.models.containers.Container | None" = None

    # Explicitly construct environment dict after computing neo4j_uri and neo4j_http_url
    environment = {
        "REDIS_URL": redis_url,
        "CELERY_BROKER_URL": redis_url,
        "CELERY_RESULT_BACKEND": redis_url,
        "NEO4J__URI": neo4j_uri,
        "NEO4J__HTTP_URL": neo4j_http_url,
        "NEO4J__USERNAME": "neo4j",
        "NEO4J__PASSWORD": "password",
    }

    try:
        image_tag = "codestory-celery-worker:test"
        command = [
            "bash",
            "-c",
            (
                # Copy current source code and use system Python with pip install
                "cp -r /host-app/src /app/ && "
                "cp -r /host-app/pyproject.toml /app/ && "
                "pip install --quiet --no-cache-dir --upgrade pydantic-core pydantic && "
                "pip install --quiet --no-cache-dir -e . && "
                "python -m uvicorn codestory_service.main:app --host 0.0.0.0 --port 8000"
            ),
        ]
        container = client.containers.run(
            image_tag,
            name=name,
            command=command,
            ports={"8000/tcp": service_port},
            volumes={
                os.getcwd(): {"bind": "/host-app", "mode": "ro"},
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            },
            working_dir="/app",
            detach=True,
            auto_remove=False,  # keep container for explicit stop() in finally
            environment=environment,
        )
        print(f"[tests] Started service container: {name} on port {service_port}")

        # ------------------------------------------------------- wait for /health
        url = f"http://localhost:{service_port}/health"
        start = time.time()
        while time.time() - start < 90:
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

        # Set environment variable for tests to know the service URL
        os.environ["CODESTORY_API_URL"] = f"http://localhost:{service_port}"
        
        yield  # --------------------------- the test(s) using this fixture execute
    finally:
        # -------------------------------------------------------------- tear-down
        if container:
            try:
                container.stop(timeout=3)
            except docker.errors.APIError as e:
                # Ignore "container already stopped/removed" races
                if not (hasattr(e, "status_code") and e.status_code in (404, 409)):
                    raise
            except Exception:
                pass
            
            try:
                container.remove(force=True)
            except docker.errors.NotFound:
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
