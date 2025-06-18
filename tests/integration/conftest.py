import multiprocessing
multiprocessing.set_start_method("fork", force=True)
import os
import subprocess

# Load .env file for OpenAI and other credentials
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def run_celery_worker(celery_cmd, env, cwd):
    subprocess.run(
        celery_cmd,
        stdout=open("celery_worker_stdout.log", "w"),
        stderr=open("celery_worker_stderr.log", "w"),
        text=True,
        env=env,
        cwd=cwd,
    )

# ---------------------------------------------------------------------------
# Environment overrides to ensure all integration tests run self-contained
# ---------------------------------------------------------------------------
os.environ["REDIS__URI"] = "redis://localhost:6379/0"
# Patch environment for Azure OpenAI endpoint/deployment
os.environ["AZURE_OPENAI__ENDPOINT"] = "https://ai-adapt-oai-eastus2.openai.azure.com"
os.environ["AZURE_OPENAI__DEPLOYMENT_ID"] = "o3"
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_HTTP_URL", "http://localhost:7475")

# Map double-underscore OpenAI env vars to single-underscore for compatibility
if "AZURE_OPENAI__ENDPOINT" in os.environ:
    os.environ["AZURE_OPENAI_ENDPOINT"] = os.environ["AZURE_OPENAI__ENDPOINT"]
if "AZURE_OPENAI__API_KEY" in os.environ:
    os.environ["AZURE_OPENAI_KEY"] = os.environ["AZURE_OPENAI__API_KEY"]

# Disable “fail-fast” behaviour in use_real_adapters so tests may fall back
# to dummy adapters if real services are unavailable.
os.environ["CODESTORY_FAIL_FAST_ADAPTERS"] = "0"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
import contextlib
def _remove_container_if_exists(container_name: str, retries: int = 5, delay: float = 1.0):
    """Remove a Docker container by name if it exists, ignoring errors."""
    import docker, time
    client = docker.from_env()
    try:
        for c in client.containers.list(all=True, filters={"name": container_name}):
            with contextlib.suppress(Exception):
                c.remove(force=True)
    except Exception:
        pass
    for _ in range(retries):
        if not any(
            c.name == container_name
            for c in client.containers.list(all=True, filters={"name": container_name})
        ):
            break
        time.sleep(delay)
    client.close()

import socket
def _find_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

# ---------------------------------------------------------------------------
# Pytest hooks – auto-mark integration tests
# ---------------------------------------------------------------------------
from pathlib import Path
import pytest, tempfile, json, time, requests

_INTEGRATION_ROOT = Path(__file__).parent.resolve()

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        item_path = Path(str(item.fspath)).resolve()
        if item_path.is_relative_to(_INTEGRATION_ROOT):
            item.add_marker(pytest.mark.integration)

# ---------------------------------------------------------------------------
# Global, lightweight service bootstrap
# ---------------------------------------------------------------------------
def _kill_existing_processes() -> int:
    """Terminate stray uvicorn / celery processes from earlier test runs."""
    import psutil, signal, time
    killed = 0
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(proc.info["cmdline"] or [])
            if "uvicorn" in cmd or "celery" in cmd:
                psutil.Process(proc.info["pid"]).terminate()
                killed += 1
        except Exception:
            continue
    if killed:
        time.sleep(2)
    return killed

@pytest.fixture(scope="session", autouse=True)
def _self_contained_environment():
    """
    Sets environment variables and ensures all integration tests run self-contained.
    Starts/stops codestory-service and codestory-worker as local subprocesses.
    """
    print("\n[pytest-setup] Preparing full integration environment")
    _kill_existing_processes()
    os.environ["CODESTORY_TEST_ENV"] = "true"
    # Start codestory-service
    service_proc = subprocess.Popen(
        ["uvicorn", "src.codestory_service.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=open("service_stdout.log", "w"),
        stderr=open("service_stderr.log", "w"),
        cwd=os.getcwd(),
        env=os.environ.copy(),
    )
    # Start codestory-worker (Celery)
    worker_proc = subprocess.Popen(
        [
            "celery",
            "-A",
            "src.codestory.ingestion_pipeline.celery_app:app",
            "worker",
            "-l",
            "info",
            "-Q",
            "high,default,low,ingestion",
        ],
        stdout=open("worker_stdout.log", "w"),
        stderr=open("worker_stderr.log", "w"),
        cwd=os.getcwd(),
        env=os.environ.copy(),
    )
    yield
    print("\n[pytest-teardown] Full integration environment finished")
    _kill_existing_processes()
    service_proc.terminate()
    worker_proc.terminate()

# ---------------------------------------------------------------------------
# Neo4j fixture – loads .cypher files into local / containerised Neo4j
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def prepare_containerized_database():
    """
    Load Cypher fixture files into Neo4j if reachable on localhost:7687.
    Falls back gracefully if Neo4j is not available.
    """
    from neo4j import GraphDatabase, basic_auth
    from neo4j.exceptions import ServiceUnavailable, AuthError
    cypher_dir = Path(__file__).parent.parent / "fixtures" / "cypher"
    files = sorted(cypher_dir.glob("*.cypher"))
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd  = os.getenv("NEO4J_PASSWORD", "password")

    try:
        driver = GraphDatabase.driver(uri, auth=basic_auth(user, pwd), connection_timeout=5)
        # Test the connection immediately
        with driver.session() as test_session:
            test_session.run("RETURN 1")
    except Exception as e:
        print(f"[neo4j-fixture] Neo4j not reachable at {uri}: {e}. Continuing without DB.")
        yield
        return

    try:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            for fp in files:
                cypher_content = fp.read_text(encoding="utf-8")
                # Split into individual statements; ignore comments and empty strings
                statements = [
                    stmt.strip()
                    for stmt in cypher_content.split(";")
                    if stmt.strip() and not stmt.strip().startswith("//")
                ]
                from neo4j.exceptions import ConstraintError
                for stmt in statements:
                    try:
                        session.execute_write(lambda tx, q=stmt: tx.run(q))
                    except ConstraintError:
                        # If fixture loaded once already in another worker, ignore duplicates
                        print(f"[neo4j-fixture] Skipping duplicate constraint/record for statement: {stmt[:60]}...")
        print("[neo4j-fixture] Database prepared with test fixtures")
    except Exception as e:
        print(f"[neo4j-fixture] Error setting up database fixtures: {e}. Continuing without fixtures.")
    finally:
        yield
        try:
            driver.close()
        except Exception:
            pass
