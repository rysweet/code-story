import multiprocessing
multiprocessing.set_start_method("fork", force=True)
import os
import subprocess

def run_celery_worker(celery_cmd, env, cwd):
    subprocess.run(
        celery_cmd,
        stdout=open("celery_worker_stdout.log", "w"),
        stderr=open("celery_worker_stderr.log", "w"),
        text=True,
        env=env,
        cwd=cwd,
    )

# Default Redis URI for integration tests (compose-mapped port 6380)
os.environ["REDIS__URI"] = "redis://localhost:6380/0"
# Ensure CodeStory settings use the same Redis URI
os.environ["CODESTORY_REDIS__URI"] = "redis://localhost:6380/0"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "True"
os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "True"

# Use compose-mapped ports for integration tests by default
os.environ.setdefault("REDIS__URI", "redis://localhost:6380/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6380/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6380/0")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
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
import neo4j

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

import subprocess
import time
import requests

def _kill_existing_processes():
    """Kill any existing uvicorn or celery processes related to code-story."""
    import psutil
    import signal
    import time
    
    killed_pids = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            # Kill uvicorn processes running code-story service
            if ('uvicorn' in cmd and 'codestory_service.main:app' in cmd) or \
               ('celery' in cmd and 'codestory' in cmd):
                print(f"[DEBUG] Killing existing process: PID={proc.info['pid']} Cmd={cmd}")
                try:
                    process = psutil.Process(proc.info['pid'])
                    process.terminate()
                    killed_pids.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
    
    # Wait for processes to terminate gracefully
    if killed_pids:
        time.sleep(2)
        
        # Force kill any that didn't terminate
        for pid in killed_pids:
            try:
                process = psutil.Process(pid)
                if process.is_running():
                    print(f"[DEBUG] Force killing PID {pid}")
                    process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    return len(killed_pids)

@pytest.fixture(scope="session", autouse=True)
def _start_services_for_integration():
    """
    Session-scoped autouse fixture that ensures clean startup/shutdown of services.
    
    1. Kills any existing uvicorn/celery processes
    2. Sets up environment for self-contained tests
    3. Tests use mocked adapters to avoid external dependencies
    4. Cleans up processes on teardown
    """
    import psutil
    import docker

    print("\n[DEBUG] _start_services_for_integration: Setting up test environment...")

    # Kill any existing processes first to ensure clean state
    killed_count = _kill_existing_processes()
    print(f"[DEBUG] Killed {killed_count} existing processes")

    # Set up environment for self-contained testing
    os.environ["CODESTORY_TEST_ENV"] = "true"
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "True"
    os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "True"
    os.environ["CELERY_BROKER_URL"] = "memory://"
    os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
    
    # Disable fail-fast adapters to allow dummy/mock adapters
    os.environ["CODESTORY_FAIL_FAST_ADAPTERS"] = "0"
    
    # Skip service startup - tests will use TestClient with mocked dependencies
    os.environ["SKIP_SERVICE_START"] = "1"

    print("[DEBUG] Environment configured for self-contained testing")
    print("[DEBUG] Tests will use TestClient with mocked adapters")
    
    yield {"message": "Self-contained test environment ready"}

    print("[DEBUG] Test environment teardown complete")


@pytest.fixture(scope="session", autouse=True)
def prepare_containerized_database():
    """
    Session-scoped autouse fixture to populate Neo4j with test data for containerized mode.
    
    - Connects to containerized Neo4j at NEO4J_URI (default bolt://localhost:7687) with neo4j/password.
    - Clears DB, then loads all Cypher files from tests/fixtures/cypher/ in sorted order.
    - Logs progress and raises RuntimeError on failure.
    - Yields to allow tests, then closes driver on teardown.
    """
    import os
    import time
    from pathlib import Path
    from neo4j import GraphDatabase, basic_auth
    from neo4j.exceptions import ServiceUnavailable, AuthError

    cypher_dir = Path(__file__).parent.parent / "fixtures" / "cypher"
    cypher_files = sorted(cypher_dir.glob("*.cypher"))
    driver = None
    
    try:
        neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        neo4j_username = os.environ.get("NEO4J_USERNAME", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
        
        print(f"[prepare_containerized_database] Connecting to Neo4j at {neo4j_uri} ...")
        
        # Wait for Neo4j container to be ready (up to 60 seconds)
        max_attempts = 60
        for attempt in range(max_attempts):
            try:
                driver = GraphDatabase.driver(
                    neo4j_uri,
                    auth=basic_auth(neo4j_username, neo4j_password),
                    max_connection_lifetime=30,
                    connection_timeout=5,
                    max_connection_pool_size=2,
                )
                # Test connection
                with driver.session() as session:
                    session.run("RETURN 1")
                print(f"[prepare_containerized_database] Connected to Neo4j after {attempt + 1} attempts")
                break
            except (ServiceUnavailable, AuthError) as e:
                if attempt < max_attempts - 1:
                    print(f"[prepare_containerized_database] Attempt {attempt + 1}/{max_attempts} failed: {e}, retrying...")
                    time.sleep(1)
                    if driver:
                        driver.close()
                        driver = None
                else:
                    raise RuntimeError(f"Failed to connect to Neo4j after {max_attempts} attempts: {e}")

        with driver.session() as session:
            print("[prepare_containerized_database] Clearing Neo4j database ...")
            session.run("MATCH (n) DETACH DELETE n")
            
            for cypher_path in cypher_files:
                try:
                    cypher = cypher_path.read_text(encoding="utf-8")
                    print(f"[prepare_containerized_database] Loading {cypher_path.name} ...")
                    session.execute_write(lambda tx: tx.run(cypher))
                except Exception as e:
                    print(f"[prepare_containerized_database] ERROR loading {cypher_path.name}: {e}")
                    raise RuntimeError(
                        f"Failed to load Cypher file {cypher_path}: {e}"
                    ) from e
        print("[prepare_containerized_database] Neo4j test database prepared.")
        yield
        
    finally:
        if driver is not None:
            driver.close()
            print("[prepare_containerized_database] Neo4j driver closed.")