import os
import glob
import re
import sys
import shutil
import multiprocessing
import socket
import subprocess
import time
import requests
from unittest.mock import patch

# NOTE: Do NOT set dummy Neo4j URIs here - this interferes with testcontainer setup
# The test_containers_and_service fixture will set the correct URIs

try:
    os.makedirs("test_container_logs", exist_ok=True)
    with open("test_container_logs/cli_integration_debug.log", "a") as f:
        f.write("[conftest DEBUG] LOGGING TEST ENTRY - FILE WRITE SUCCESSFUL\n")
    with open("cli_integration_debug.log", "a") as f:
        f.write("[conftest DEBUG] LOGGING TEST ENTRY - FILE WRITE SUCCESSFUL (cwd)\n")
except Exception as e:
    print(f"[conftest DEBUG] Failed to write to cli_integration_debug.log at import: {e}")

multiprocessing.set_start_method("fork", force=True)

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import pytest
from dotenv import load_dotenv

# =======================
# Pytest Plugin Functions
# =======================

def pytest_addoption(parser):
    """Add command line options for integration tests."""
    parser.addoption(
        "--skip-neo4j",
        action="store_true",
        default=False,
        help="Skip tests that require Neo4j",
    )
    parser.addoption(
        "--skip-celery",
        action="store_true",
        default=False,
        help="Skip tests that require Celery",
    )
    parser.addoption(
        "--run-neo4j",
        action="store_true",
        default=False,
        help="[DEPRECATED] Use --skip-neo4j=False instead",
    )
    parser.addoption(
        "--run-celery",
        action="store_true",
        default=False,
        help="[DEPRECATED] Use --skip-celery=False instead",
    )

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "neo4j: mark test as requiring Neo4j")
    config.addinivalue_line("markers", "celery: mark test as requiring Celery")

def pytest_collection_modifyitems(config, items):
    """Enable Neo4j and Celery tests by default."""
    skip_neo4j = pytest.mark.skip(reason="Tests using Neo4j are disabled with --skip-neo4j")
    skip_celery = pytest.mark.skip(reason="Tests using Celery are disabled with --skip-celery")
    if config.getoption("--skip-neo4j", False):
        for item in items:
            if "neo4j" in item.keywords:
                item.add_marker(skip_neo4j)
    if config.getoption("--skip-celery", False):
        for item in items:
            if "celery" in item.keywords:
                item.add_marker(skip_celery)

# =======================
# Environment Setup
# =======================

@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """Mock the settings module to use test settings."""
    from .integration.test_config import get_test_settings
    with patch("codestory.config.settings.get_settings", return_value=get_test_settings()):
        yield

@pytest.fixture(scope="session")
def neo4j_env():
    """Setup Neo4j environment variables for tests."""
    ci_env = os.environ.get("CI") == "true"
    docker_env = os.environ.get("CODESTORY_IN_CONTAINER") == "true"
    neo4j_port = "7687" if ci_env else ("7689" if docker_env else "7688")
    if docker_env:
        neo4j_uri = "bolt://neo4j:7687"
        redis_uri = "redis://redis:6379/0"
        redis_host = "redis"
        redis_port = "6379"
    else:
        neo4j_uri = f"bolt://localhost:{neo4j_port}"
        redis_host = "localhost"
        redis_port = "6380"
        redis_uri = f"redis://{redis_host}:{redis_port}/0"
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["NEO4J__URI"] = neo4j_uri
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "neo4j"
    os.environ["REDIS_URI"] = redis_uri
    os.environ["REDIS__URI"] = redis_uri
    os.environ["REDIS_HOST"] = redis_host
    os.environ["REDIS_PORT"] = redis_port
    os.environ["CELERY_BROKER_URL"] = redis_uri
    os.environ["CELERY_RESULT_BACKEND"] = redis_uri

@pytest.fixture(scope="session", autouse=True)
def load_env_vars():
    """Load environment variables for integration tests."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    load_dotenv(env_path)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    ci_env = os.environ.get("CI") == "true"
    docker_env = os.environ.get("CODESTORY_IN_CONTAINER") == "true"
    neo4j_port = "7687" if ci_env else ("7689" if docker_env else "7688")
    if docker_env:
        neo4j_uri = "bolt://neo4j:7687"
        redis_uri = "redis://redis:6379/0"
        redis_host = "redis"
        redis_port = "6379"
    else:
        neo4j_uri = f"bolt://localhost:{neo4j_port}"
        redis_host = "localhost"
        redis_port = "6380"
        redis_uri = f"redis://{redis_host}:{redis_port}/0"
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["NEO4J__URI"] = neo4j_uri
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "neo4j"
    os.environ["REDIS_URI"] = redis_uri
    os.environ["REDIS__URI"] = redis_uri
    os.environ["REDIS_HOST"] = redis_host
    os.environ["REDIS_PORT"] = redis_port
    os.environ["CELERY_BROKER_URL"] = redis_uri
    os.environ["CELERY_RESULT_BACKEND"] = redis_uri
    os.environ["OPENAI_API_KEY"] = "sk-test-key-openai"
    os.environ["OPENAI__API_KEY"] = "sk-test-key-openai"

# =======================
# Fixtures
# =======================

@pytest.fixture(scope="session")
def neo4j_connector(test_containers_and_service):
    """Return a Neo4j connector for tests, ensuring the test container is started."""
    from codestory.config.settings import get_settings
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    import os

    # Use the environment variables set by test_containers_and_service (priority order)
    uri = (
        os.environ.get("CODESTORY_NEO4J__URI") or
        os.environ.get("NEO4J__URI") or
        os.environ.get("NEO4J_URI") or
        test_containers_and_service["neo4j_uri"]
    )
    username = (
        os.environ.get("CODESTORY_NEO4J__USERNAME") or
        os.environ.get("NEO4J__USERNAME") or
        os.environ.get("NEO4J_USERNAME") or
        "neo4j"
    )
    password = (
        os.environ.get("CODESTORY_NEO4J__PASSWORD") or
        os.environ.get("NEO4J__PASSWORD") or
        os.environ.get("NEO4J_PASSWORD") or
        "password"
    )
    database = (
        os.environ.get("CODESTORY_NEO4J__DATABASE") or
        os.environ.get("NEO4J__DATABASE") or
        os.environ.get("NEO4J_DATABASE") or
        "neo4j"
    )

    # Force settings reload to pick up testcontainer environment variables
    get_settings.cache_clear()  # type: ignore[attr-defined]

    print(f"[neo4j_connector] Connecting with uri={uri}, username={username}, password={password}")
    connector = Neo4jConnector(
        uri=uri,
        username=username,
        password=password,
        database=database,
    )
    try:
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        print("Neo4j database cleared for clean test.")
    except Exception as e:
        print(f"Warning: Could not clear Neo4j database: {e}")
    yield connector
    try:
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        print("Neo4j database cleaned up after test.")
    except Exception as e:
        print(f"Warning: Could not clean up Neo4j database: {e}")
    try:
        connector.close()
    except Exception as e:
        print(f"Warning: Error closing Neo4j connection: {e}")

@pytest.fixture(scope="function")
def redis_client():
    """Create a Redis client for testing and manage cleanup."""
    import redis
    redis_uri = (
        os.environ.get("REDIS__URI") or os.environ.get("REDIS_URI") or "redis://localhost:6380/0"
    )
    client = redis.from_url(redis_uri)
    try:
        client.flushdb()
        print("Redis database cleared for clean test.")
    except Exception as e:
        print(f"Warning: Could not clear Redis database: {e}")
    yield client
    try:
        client.flushdb()
        print("Redis database cleaned up after test.")
    except Exception as e:
        print(f"Warning: Could not clean up Redis database: {e}")

@pytest.fixture(scope="function")
def celery_app(redis_client):
    """Provide a Celery app configured for integration testing."""
    import importlib
    from codestory.ingestion_pipeline.celery_app import app
    redis_uri = (
        os.environ.get("REDIS__URI") or os.environ.get("REDIS_URI") or "redis://localhost:6380/0"
    )
    app.conf.update(
        broker_url=redis_uri,
        result_backend=redis_uri,
        task_always_eager=True,
        task_eager_propagates=True,
        task_ignore_result=False,
        worker_send_task_events=False,
        broker_connection_retry=True,
        broker_connection_max_retries=3,
    )
    try:
        app.control.purge()
        print("Celery task queue purged for clean test.")
    except Exception as e:
        print(f"Warning: Could not purge Celery tasks: {e}")
    task_modules = [
        "codestory.ingestion_pipeline.tasks",
        "codestory_filesystem.step",
        "codestory_blarify.step",
        "codestory_summarizer.step",
        "codestory_docgrapher.step",
    ]
    for module_name in task_modules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            print(f"Warning: Could not import task module {module_name}: {e}")
    app.finalize()
    yield app
    try:
        app.control.purge()
        print("Celery task queue purged after test.")
    except Exception as e:
        print(f"Warning: Could not purge Celery tasks after test: {e}")
    app.conf.update(
        task_always_eager=False,
    )

import os
import pytest
import time
from testcontainers.neo4j import Neo4jContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def test_containers_and_service():
    """
    Session-scoped fixture to bring up Neo4j and Redis testcontainers,
    set environment variables, and wait for services to be ready.
    """
    neo4j_container = Neo4jContainer("neo4j:5.19")
    redis_container = RedisContainer("redis:7.2.4")

    neo4j_container.with_env("NEO4J_AUTH", "neo4j/password")
    neo4j_container.with_exposed_ports(7687)
    redis_container.with_exposed_ports(6379)

    neo4j = neo4j_container.start()
    redis = redis_container.start()

    neo4j_bolt_port = neo4j.get_exposed_port(7687)
    redis_port = redis.get_exposed_port(6379)

    neo4j_uri = f"bolt://localhost:{neo4j_bolt_port}"
    redis_uri = f"redis://localhost:{redis_port}/0"

    # Set environment variables for all subprocesses
    # CRITICAL: Set CODESTORY_NEO4J__URI which has highest precedence in settings
    os.environ["CODESTORY_NEO4J__URI"] = neo4j_uri
    os.environ["CODESTORY_NEO4J__USERNAME"] = "neo4j"
    os.environ["CODESTORY_NEO4J__PASSWORD"] = "password"
    os.environ["CODESTORY_NEO4J__DATABASE"] = "neo4j"
    # Also set alternative variable names for compatibility
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["NEO4J__URI"] = neo4j_uri
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "neo4j"
    # Redis configuration
    os.environ["CODESTORY_REDIS__URI"] = redis_uri
    os.environ["REDIS_URI"] = redis_uri
    os.environ["REDIS__URI"] = redis_uri
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = str(redis_port)
    os.environ["CELERY_BROKER_URL"] = redis_uri
    os.environ["CELERY_RESULT_BACKEND"] = redis_uri
    
    # Clear settings cache to ensure new environment variables are used
    try:
        from codestory.config.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        print(f"[test_containers_and_service] Settings cache cleared, Neo4j URI: {neo4j_uri}")
    except Exception as e:
        print(f"[test_containers_and_service] Warning: Could not clear settings cache: {e}")

    # Wait for Neo4j to be ready
    import socket
    for _ in range(60):
        try:
            s = socket.create_connection(("localhost", int(neo4j_bolt_port)), timeout=2)
            s.close()
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Neo4j testcontainer did not become ready in time")

    # Wait for Redis to be ready
    import redis as redis_py
    for _ in range(60):
        try:
            client = redis_py.Redis(host="localhost", port=int(redis_port))
            client.ping()
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Redis testcontainer did not become ready in time")

    yield {
        "neo4j_uri": neo4j_uri,
        "redis_uri": redis_uri,
        "neo4j_bolt_port": neo4j_bolt_port,
        "redis_port": redis_port,
    }

    neo4j.stop()
    redis.stop()
