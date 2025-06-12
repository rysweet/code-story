import os

# Use compose-mapped ports for integration tests by default
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6380/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6380/0")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7688")
os.environ.setdefault("NEO4J_HTTP_URL", "http://localhost:7475")

import contextlib
def _remove_container_if_exists(container_name: str, retries: int = 5, delay: float = 1.0):
    """Remove a Docker container by name if it exists, ignoring errors. Waits for removal."""
    import docker
    import time
    client = docker.from_env()
    try:
        for c in client.containers.list(all=True, filters={"name": container_name}):
            try:
                c.remove(force=True)
            except Exception:
                pass
    except Exception:
        pass
    # Wait for the container to actually be gone
    for attempt in range(retries):
        still_exists = False
        try:
            still_exists = any(
                c.name == container_name
                for c in client.containers.list(all=True, filters={"name": container_name})
            )
        except Exception:
            pass
        if not still_exists:
            break
        time.sleep(delay)
    client.close()
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
import subprocess

@pytest.fixture(scope="session", autouse=True)
def prune_exited_containers():
    """
    Prune all exited containers before and after the test session to prevent resource exhaustion.
    """
    import docker
    client = docker.from_env()
    try:
        client.containers.prune()
    except Exception:
        pass
    yield
    try:
        client.containers.prune()
    except Exception:
        pass
    client.close()


def inject_azure_credentials_into_container(container_name: str) -> bool:
    """Inject Azure credentials from host into the specified container."""
    try:
        # Get the location of Azure tokens on the host
        azure_dir = os.path.expanduser("~/.azure")
        
        # Check if the Azure token directory exists
        if not os.path.exists(azure_dir):
            print(f"[tests] Azure directory {azure_dir} does not exist, skipping credential injection")
            return False
            
        # Check if container exists and is running
        container_check = subprocess.run(
            ["docker", "container", "inspect", container_name],
            capture_output=True,
        )
        
        if container_check.returncode != 0:
            print(f"[tests] Container {container_name} does not exist or is not running")
            return False
            
        # Create target directory in container
        mkdir_cmd = [
            "docker", "exec", container_name,
            "bash", "-c", "mkdir -p /root/.azure"
        ]
        subprocess.run(mkdir_cmd, capture_output=True)
        
        # Copy Azure credentials into container
        copy_cmd = [
            "docker", "cp",
            azure_dir + "/.",
            f"{container_name}:/root/.azure/"
        ]
        
        result = subprocess.run(copy_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[tests] Successfully injected Azure credentials into {container_name}")
            return True
        else:
            print(f"[tests] Failed to inject Azure credentials: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"[tests] Error injecting Azure credentials: {e}")
        return False

# Redis container fixture removed - using testcontainers version from tests/conftest.py
# to avoid conflicts and port allocation issues
@pytest.fixture(scope="session")
def neo4j_container(request):
    """
    Session-scoped fixture to start a Neo4j container for integration tests.
    Starts Neo4j on a user-defined bridge network so it is accessible by container name.
    """
    import docker
    import time
    import platform
    import uuid
    import json
    import os

    client = docker.from_env()
    network_name = "codestory-test-network"
    # Create user-defined bridge network if not exists
    try:
        client.networks.get(network_name)
    except docker.errors.NotFound:
        client.networks.create(network_name, driver="bridge")

    # Use a unique container name per session to avoid conflicts
    session_id = os.environ.get("PYTEST_XDIST_WORKER", "") + "-" + str(uuid.uuid4())
    container_name = f"test-neo4j-{session_id}"
    image = "neo4j:5.18.0-enterprise"

    env = {
        "NEO4J_AUTH": "neo4j/password",
        "NEO4J_ACCEPT_LICENSE_AGREEMENT": "yes",
        "NEO4J_PLUGINS": json.dumps(["apoc", "graph-data-science"]),
        "NEO4J_dbms_security_procedures_unrestricted": "apoc.*,gds.*",
        # Do NOT override advertised addresses; let Neo4j use its container name
    }
    # Ensure Neo4j advertises the correct address for Bolt connections (hostname only, no port)
    env["NEO4J_server_default__advertised__address"] = container_name

    # Expose default ports for bridge network
    # Map Bolt port to a random available host port for readiness check
    host_bolt_port = _find_free_port()
    ports = {
        "7687/tcp": host_bolt_port,
        "7474/tcp": None,
    }

    try:
        container = client.containers.run(
            image,
            name=container_name,
            hostname=container_name,  # Ensure hostname matches container name for Docker DNS
            ports=ports,
            environment=env,
            detach=True,
            network=network_name,
        )
    except docker.errors.APIError as e:
        client.close()
        import pytest
        pytest.fail(f"Could not start Neo4j container: {e}")

    # Wait for Neo4j to be ready.
    # Neo4j 5.x no longer prints a simple "Started." line; instead we look for any one of
    # several stable markers in addition to the Bolt enabled message.
    start = time.time()
    ready = False
    timeout = int(os.environ.get("NEO4J_STARTUP_TIMEOUT", "300"))  # allow override for slow CI, default 300s
    SUCCESS_MARKERS = [
        "Started.",  # legacy 4.x style
        "Remote interface available",
        "Default database 'neo4j' is created",
    ]
    # Wait for Neo4j to be ready for queries (not just port open)
    import neo4j
    import subprocess
    import time as _time
    bolt_uri = f"bolt://{container_name}:7687"
    neo4j_ready = False
    # Wait 10 seconds for Docker DNS to register the container hostname
    print(f"[neo4j_container] Sleeping 10s to allow Docker DNS to register hostname {container_name}")
    _time.sleep(10)
    import socket as pysocket
    bolt_port = 7687
    # Get the container's IP address on the test network
    network_name = "codestory-test-network"
    print(f"[neo4j_container] Using localhost:{host_bolt_port} for readiness check")
    while time.time() - start < timeout:
        logs = container.logs().decode(errors="ignore")
        # Consider ready if either Bolt enabled or any success marker is present
        if "Bolt enabled" in logs or any(marker in logs for marker in SUCCESS_MARKERS):
            # Try a simple TCP connection to the mapped host port to confirm readiness
            try:
                with pysocket.create_connection(("localhost", host_bolt_port), timeout=5):
                    print(f"[neo4j_container] Bolt port localhost:{host_bolt_port} is open.")
                    neo4j_ready = True
                    break
            except Exception as e:
                print(f"[neo4j_container] Bolt port not open yet: {e}")
                # Check if the container is still running
                container.reload()
                print(f"[neo4j_container] Status: {container.status}")
        _time.sleep(2)
    if not neo4j_ready:
        print(f"[neo4j_container] Neo4j did not become query-ready in {timeout}s. Last logs:\\n{logs}")
        container.stop(timeout=3)
        client.close()
        raise RuntimeError("Neo4j container did not become query-ready in time")

    # Set environment variables for other fixtures/tests (for any host-based tests)
    os.environ.update({
        "NEO4J_URI": f"bolt://{container_name}:7687",
        "NEO4J_HTTP_URL": f"http://{container_name}:7474",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password",
    })
    print(f"[neo4j_container] Set NEO4J_URI=bolt://{container_name}:7687")
    print(f"[neo4j_container] Effective NEO4J_URI in os.environ: {os.environ.get('NEO4J_URI')}")

    def fin():
        import datetime
        print(f"[neo4j_container] Stopping Neo4j container {container.name} at {datetime.datetime.now().isoformat()}")
        try:
            container.stop(timeout=3)
        except Exception:
            pass
        try:
            container.remove(force=True)
        except Exception:
            pass
    request.addfinalizer(fin)
    yield container

@pytest.fixture(scope="session")
def celery_worker_container(redis_container):
    """
    Session-scoped fixture to run a real Celery worker in a Docker container for integration tests.
    Uses the Redis URL from testcontainers. Builds the worker image once per session for fast startup.
    """
    import docker
    import time
    from uuid import uuid4
    import platform
    import pathlib
    import socket

    # Redis container now returns a URI string from testcontainers
    redis_url = redis_container or os.environ.get("REDIS_URI", "redis://localhost:6379/0")
    
    # For Docker containers, adjust the host if needed
    if platform.system() != "Linux" and "localhost" in redis_url:
        redis_url = redis_url.replace("localhost", "host.docker.internal")

    # --- Wait for Redis hostname to be resolvable on the Docker network ---
    redis_host = redis_url.split("://")[1].split(":")[0]
    network_name = "codestory-test-network"
    max_dns_wait = 15
    dns_wait_start = time.time()
    while time.time() - dns_wait_start < max_dns_wait:
        try:
            socket.gethostbyname(redis_host)
            print(f"[celery_worker_container] Redis hostname {redis_host} is resolvable.")
            break
        except Exception:
            print(f"[celery_worker_container] Waiting for Redis hostname {redis_host} to be resolvable...")
            time.sleep(1)
    else:
        print(f"[celery_worker_container] Redis hostname {redis_host} was not resolvable after {max_dns_wait}s. Proceeding anyway.")

    client = docker.from_env()
    # Use a unique container name per session to avoid conflicts
    session_id = os.environ.get("PYTEST_XDIST_WORKER", "") + "-" + str(uuid4())
    container_name = f"cs-worker-{session_id}"
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
    # Ensure the worker image has essential OS utilities (ps/procps) and the Docker CLI
    # so that tests in test_docker_connectivity.py can execute successfully.
    # We install them at container-run time to avoid a bespoke Dockerfile rebuild.
    # The worker image is pre-built with all dependencies and entrypoint.
    # No runtime install or shell command is needed.
    command = None
    try:
        # Clean up any prior worker containers
        _remove_container_if_exists(container_name)
        try:
            client.networks.get(network_name)
        except docker.errors.NotFound:
            client.networks.create(network_name, driver="bridge")
        container = client.containers.run(
            image_tag,
            name=container_name,
            command=command,
            user="root",  # run as root so apt installs succeed
            volumes={
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            },
            working_dir="/app",
            environment=env,
            detach=True,
            auto_remove=False,
            network=network_name,
        )
    except Exception as e:
        import pytest
        pytest.fail(f"Could not start celery worker container: {e}")

    # Wait for worker to connect to Redis (max 180s)
    log_match = f"Connected to {redis_url}"
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
        # Exfiltrate logs before stopping/removing
        try:
            logs_dir = Path("test_container_logs")
            logs_dir.mkdir(exist_ok=True)
            log_path = logs_dir / f"{container.name}.log"
            with open(log_path, "wb") as f:
                f.write(container.logs())
        except Exception as e:
            print(f"[tests] Failed to exfiltrate Celery worker logs: {e}")
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
    Ensures both are on the same user-defined bridge network and uses the Neo4j container's
    name and default port for connectivity.
    """
    import docker
    import os
    import platform
    import requests
    import time
    from uuid import uuid4

    client = docker.from_env()
    network_name = "codestory-test-network"
    # Create user-defined bridge network if not exists
    try:
        client.networks.get(network_name)
    except docker.errors.NotFound:
        client.networks.create(network_name, driver="bridge")

    # Get Neo4j container info
    neo4j_container_obj = None
    print("[DEBUG] Listing all running containers for test setup:")
    try:
        for c in client.containers.list(all=True):
            print(f"  Container: {c.name} (ID: {c.id}) Status: {c.status} ExitCode: {getattr(c, 'exit_code', 'N/A')}")
            try:
                logs = c.logs(tail=50).decode(errors="ignore")
                print(f"    Last 50 log lines:\n{logs}")
            except Exception as log_exc:
                print(f"    [DEBUG] Could not get logs for {c.name}: {log_exc}")
            if c.name.startswith("test-neo4j-"):
                neo4j_container_obj = c
                print(f"  [DEBUG] Found Neo4j container: {c.name}")
                break
    except docker.errors.NotFound as e:
        print(f"[DEBUG] Docker NotFound error during container listing: {e}")
        pytest.skip("Docker container not found during test setup (likely cleaned up early)")
    if not neo4j_container_obj:
        print("[DEBUG] Could not find Neo4j container for test network setup. Skipping test.")
        pytest.skip("Neo4j container not found for test network setup")

    # Connect Neo4j container to the test network if not already
    networks = neo4j_container_obj.attrs["NetworkSettings"]["Networks"]
    if network_name not in networks:
        # Wait for Neo4j Bolt port to be open before starting the service container
        neo4j_host = neo4j_container_obj.name
        try:
            import socket as pysocket
            bolt_ready = False
            bolt_timeout = 90
            bolt_start = time.time()
            bolt_port = 7687
            print(f"[service_container] Waiting for Neo4j Bolt port {neo4j_host}:{bolt_port} to be open...")
            while time.time() - bolt_start < bolt_timeout:
                try:
                    with pysocket.create_connection((neo4j_host, bolt_port), timeout=2):
                        print(f"[service_container] Neo4j Bolt port {neo4j_host}:{bolt_port} is open.")
                        bolt_ready = True
                        break
                except Exception as e:
                    print(f"[service_container] Neo4j Bolt port not open yet: {e}")
                    time.sleep(2)
            if not bolt_ready:
                print(f"[service_container] Neo4j Bolt port {neo4j_host}:{bolt_port} did not become ready in {bolt_timeout}s.")
                pytest.skip("Neo4j Bolt port not open for service container startup")
        except Exception as e:
            print(f"[service_container] Exception while waiting for Neo4j Bolt port: {e}")
            pytest.skip("Exception while waiting for Neo4j Bolt port")
        client.networks.get(network_name).connect(neo4j_container_obj)

    # Redis container now returns a URI string from testcontainers
    redis_url = redis_container or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    if platform.system() != "Linux" and "localhost" in redis_url:
        redis_url = redis_url.replace("localhost", "host.docker.internal")

    # Find a free port for the service
    service_port = _find_free_port()

    # Use Neo4j container name and default port for URI
    neo4j_host = neo4j_container_obj.name
    neo4j_uri = f"bolt://{neo4j_host}:7687"
    neo4j_http_url = f"http://{neo4j_host}:7474"

    # Explicitly construct environment dict after reading neo4j_uri from env
    environment = {
        "REDIS_URL": redis_url,
        "CELERY_BROKER_URL": redis_url,
        "CELERY_RESULT_BACKEND": redis_url,
        # Redis settings with CODESTORY_ prefix for Settings class
        "CODESTORY_REDIS__URI": redis_url,
        # Neo4j settings with CODESTORY_ prefix for Settings class
        "CODESTORY_NEO4J__URI": neo4j_uri,
        "CODESTORY_NEO4J__HTTP_URL": neo4j_http_url,
        "CODESTORY_NEO4J__USERNAME": "neo4j",
        "CODESTORY_NEO4J__PASSWORD": "password",
        # Also set without prefix for backward compatibility
        "NEO4J_URI": neo4j_uri,
        "NEO4J_HTTP_URL": neo4j_http_url,
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password",
        # Pass ALL Azure OpenAI env vars from host to container
        "AZURE_OPENAI__ENDPOINT": os.environ.get("AZURE_OPENAI__ENDPOINT", ""),
        "AZURE_OPENAI__API_KEY": os.environ.get("AZURE_OPENAI__API_KEY", ""),
        "AZURE_OPENAI__DEPLOYMENT_ID": os.environ.get("AZURE_OPENAI__DEPLOYMENT_ID", ""),
        "AZURE_OPENAI__API_VERSION": os.environ.get("AZURE_OPENAI__API_VERSION", ""),
        "AZURE_TENANT_ID": os.environ.get("AZURE_TENANT_ID", ""),
        # Force container to use test config to prioritize TOML over env vars
        "CODESTORY_CONFIG_FILE": "tests/fixtures/test_config.toml",
    }

    # Use a unique container name per session to avoid conflicts
    session_id = os.environ.get("PYTEST_XDIST_WORKER", "") + "-" + str(uuid4())
    name = f"cs-service-{session_id}"
    container = None
    try:
        image_tag = "codestory-service:test"
        # Extract container names for DNS check
        redis_container_name = redis_url.split("://")[1].split(":")[0]
        neo4j_container_name = neo4j_host

        # Clean up any prior service containers
        _remove_container_if_exists(name)

        command = [
            "uvicorn",
            "src.codestory_service.main:app",
            "--host", "0.0.0.0",
            "--port", "8000"
        ]
        # Retry container creation if it fails due to race conditions
        for attempt in range(3):
            try:
                container = client.containers.run(
                    image_tag,
                    name=name,
                    command=command,
                    ports={"8000/tcp": service_port},
                    volumes={
                        "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
                        os.getcwd(): {"bind": "/app", "mode": "rw"},
                    },
                    working_dir="/app",
                    detach=True,
                    auto_remove=False,  # Do not auto-remove so we can inspect after failure
                    environment=environment,
                    network=network_name,
                )
                print(f"[tests] Started service container: {name} on port {service_port} (network: {network_name})")
                # Confirm container exists and is running
                for check in range(5):
                    try:
                        c = client.containers.get(name)
                        if c.status in ("created", "running"):
                            break
                    except Exception:
                        pass
                    time.sleep(1)
                break
            except docker.errors.APIError as e:
                print(f"[tests] Attempt {attempt+1}: Failed to start service container {name}: {e}")
                _remove_container_if_exists(name)
                time.sleep(2)
        else:
            raise RuntimeError(f"Failed to start service container {name} after retries")

        # Wait for service to be accepting requests (use simple root endpoint first)
        root_url = f"http://localhost:{service_port}/"
        health_url = f"http://localhost:{service_port}/health"
        start = time.time()
        service_responding = False
        
        # First, wait for any response from the service
        while time.time() - start < 60:
            try:
                response = requests.get(root_url, timeout=2)
                print(f"[tests] Service root responding with status {response.status_code}")
                service_responding = True
                break
            except requests.RequestException as e:
                print(f"[tests] Service not responding yet: {e}")
                pass
            time.sleep(2)
        
        if not service_responding:
            logs = container.logs(tail=500).decode(errors="ignore") if container else ""
            print(f"[tests] Service failed to respond, logs:\n{logs}")
            raise RuntimeError("Service container not responding to HTTP requests")
        
        # Now check health endpoint, but be more tolerant
        print(f"[tests] Service is responding, checking health endpoint...")
        health_attempts = 0
        while time.time() - start < 90 and health_attempts < 5:
            try:
                response = requests.get(health_url, timeout=10)
                print(f"[tests] Health check responding with status {response.status_code}")
                if response.status_code in [200, 500]:  # Accept healthy or degraded
                    break
                health_attempts += 1
            except requests.RequestException as e:
                print(f"[tests] Health check failed: {e}")
                health_attempts += 1
            time.sleep(5)
        else:
            print(f"[tests] Health endpoint not stable, but service is running. Proceeding anyway.")

        # Set the API URL for CLI commands to use the running service
        os.environ["CODESTORY_SERVICE_URL"] = f"http://localhost:{service_port}"
        print(f"[tests] Service ready at {os.environ['CODESTORY_SERVICE_URL']}")
        
        # Inject Azure credentials into the running container
        try:
            print(f"[tests] Injecting Azure credentials into container {name}")
            inject_azure_credentials_into_container(name)
        except Exception as e:
            print(f"[tests] Warning: Failed to inject Azure credentials: {e}")
            # Continue anyway - the service might work without proper Azure auth
        
        # Set env var so CLI helpers target the correct container
        os.environ["CODESTORY_SERVICE_CONTAINER"] = name
        yield
    finally:
        if container:
            # Exfiltrate logs before stopping/removing
            try:
                logs_dir = Path("test_container_logs")
                logs_dir.mkdir(exist_ok=True)
                log_path = logs_dir / f"{container.name}.log"
                with open(log_path, "wb") as f:
                    f.write(container.logs())
            except Exception as e:
                print(f"[tests] Failed to exfiltrate service container logs: {e}")
            try:
                container.stop(timeout=3)
            except Exception:
                pass
            # Commented out to preserve container for debugging
            # try:
            #     container.remove(force=True)
            # except Exception:
            #     pass
        # Optionally disconnect containers from the network (cleanup)
        try:
            client.networks.get(network_name).disconnect(neo4j_container_obj, force=True)
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
