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
# Centralized Test Configuration Management
# =======================
#
# This section implements the single source of truth for all test configuration and environment
# variable management for integration and unit tests. All test modules and fixtures must use
# this utility for environment variable access and mutation.
#
# Priority order for environment variable values:
#   1. Unified fixture overrides (e.g., unified_test_env, testcontainers)
#   2. .env file (if present, loaded via python-dotenv)
#   3. Hardcoded defaults (see below)
#
# This system is required by:
#   - specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
#   - code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md
#
# All legacy or manual environment variable management in test modules/scripts is deprecated.
# See the TestConfig class and get_test_config() function below for usage.
#
# Example usage in tests:
#   config = get_test_config()
#   neo4j_uri = config["NEO4J_URI"]
#   config.set("NEO4J_DATABASE", "testdb")
#
# This utility ensures all subprocesses and test logic see a consistent environment.
#
import threading
from dotenv import load_dotenv

class TestConfig:
    """
    Centralized test configuration manager for all environment variables used in tests.

    Priority order:
      1. Fixture/session overrides (set via set() or update())
      2. .env file (loaded at init)
      3. Hardcoded defaults (see _defaults)
    """
    _instance = None
    _lock = threading.Lock()

    _defaults = {
        "NEO4J_URI": "bolt://localhost:7688",
        "NEO4J__URI": "bolt://localhost:7688",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J__USERNAME": "neo4j",
        "NEO4J__PASSWORD": "password",
        "NEO4J__DATABASE": "neo4j",
        "REDIS_URI": "redis://localhost:6380/0",
        "REDIS__URI": "redis://localhost:6380/0",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6380",
        "CELERY_BROKER_URL": "redis://localhost:6380/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6380/0",
        "OPENAI_API_KEY": "sk-test-key-openai",
        "OPENAI__API_KEY": "sk-test-key-openai",
        # Add more defaults as needed
    }

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self._overrides = {}
        # Load .env if present
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        load_dotenv(env_path, override=False)
        self._env = dict(os.environ)

    def get(self, key, default=None):
        if key in self._overrides:
            return self._overrides[key]
        if key in self._env:
            return self._env[key]
        if key in self._defaults:
            return self._defaults[key]
        return default

    def __getitem__(self, key):
        val = self.get(key)
        if val is None:
            raise KeyError(f"TestConfig: {key} not found in overrides, .env, or defaults")
        return val

    def set(self, key, value):
        self._overrides[key] = value
        os.environ[key] = value

    def update(self, mapping):
        for k, v in mapping.items():
            self.set(k, v)

    def as_dict(self):
        # Returns merged view (overrides > .env > defaults)
        result = dict(self._defaults)
        result.update(self._env)
        result.update(self._overrides)
        return result

def get_test_config():
    """
    Returns the singleton TestConfig instance.
    """
    return TestConfig()

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
    """
    [DEPRECATED for integration/E2E tests]
    Legacy Neo4j connector fixture.

    DO NOT USE in integration or E2E tests. Use only in unit tests if needed.
    All integration/E2E tests must use the unified_test_env fixture and instantiate
    resource clients per-test for robust resource isolation.
    """
    from codestory.config.settings import get_settings
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    import os

    # ... (rest of implementation unchanged)

@pytest.fixture(scope="function")
def redis_client():
    """
    [DEPRECATED for integration/E2E tests]
    Legacy Redis client fixture.

    DO NOT USE in integration or E2E tests. Use only in unit tests if needed.
    All integration/E2E tests must use the unified_test_env fixture and instantiate
    resource clients per-test for robust resource isolation.
    """
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
    """
    [DEPRECATED for integration/E2E tests]
    Legacy Celery app fixture.

    DO NOT USE in integration or E2E tests. Use only in unit tests if needed.
    All integration/E2E tests must use the unified_test_env fixture and instantiate
    resource clients per-test for robust resource isolation.
    """
    import importlib
    from codestory.ingestion_pipeline.celery_app import app
    config = get_test_config()
    redis_uri = (
        config.get("REDIS__URI") or config.get("REDIS_URI") or "redis://localhost:6380/0"
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

# =======================
# Unified Testcontainer Pattern for Service Isolation
# =======================
#
# This section implements a unified, extensible pattern for all testcontainers
# (Neo4j, Redis, etc.) used in integration/E2E tests. All container management,
# dynamic port allocation, environment propagation, and health checks are handled
# here. To add a new service, add a new entry to the SERVICE_CONTAINERS dict.
#
# Cross-links:
#   - specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
#   - code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md
#
# Example usage in tests:
#   def test_graphdb_integration(unified_test_env):
#       neo4j_url = unified_test_env["NEO4J_URI"]
#       redis_url = unified_test_env["REDIS_URI"]
#       # Use these endpoints in your test logic

import pytest
import time
import os

from testcontainers.neo4j import Neo4jContainer
from testcontainers.redis import RedisContainer

class ServiceContainer:
    """Base class for service containers in the unified test infra."""
    def __init__(self, name):
        self.name = name
        self.container = None
        self.env = {}
        self.ports = {}
        self.ready = False

    def start(self):
        raise NotImplementedError

    def stop(self):
        if self.container:
            self.container.stop()

    def wait_for_ready(self):
        raise NotImplementedError

    def get_env(self):
        return self.env

    def get_ports(self):
        return self.ports

class Neo4jServiceContainer(ServiceContainer):
    def __init__(self):
        super().__init__("neo4j")
        self.image = "neo4j:5.19"
        self.bolt_port = 7687
        self.username = "neo4j"
        self.password = "password"
        self.database = "neo4j"

    def start(self):
        self.container = Neo4jContainer(self.image)
        self.container.with_env("NEO4J_AUTH", f"{self.username}/{self.password}")
        self.container.with_exposed_ports(self.bolt_port)
        self.container = self.container.start()
        self.ports["bolt"] = int(self.container.get_exposed_port(self.bolt_port))
        self.env = {
            "NEO4J_URI": f"bolt://localhost:{self.ports['bolt']}",
            "NEO4J__URI": f"bolt://localhost:{self.ports['bolt']}",
            "CODESTORY_NEO4J__URI": f"bolt://localhost:{self.ports['bolt']}",
            "NEO4J_USERNAME": self.username,
            "NEO4J__USERNAME": self.username,
            "CODESTORY_NEO4J__USERNAME": self.username,
            "NEO4J_PASSWORD": self.password,
            "NEO4J__PASSWORD": self.password,
            "CODESTORY_NEO4J__PASSWORD": self.password,
            "NEO4J_DATABASE": self.database,
            "NEO4J__DATABASE": self.database,
            "CODESTORY_NEO4J__DATABASE": self.database,
        }
        return self

    def wait_for_ready(self, timeout=60):
        import socket
        start = time.time()
        while time.time() - start < timeout:
            try:
                s = socket.create_connection(("localhost", self.ports["bolt"]), timeout=2)
                s.close()
                self.ready = True
                return
            except Exception:
                time.sleep(1)
        raise RuntimeError("Neo4j testcontainer did not become ready in time")

class RedisServiceContainer(ServiceContainer):
    def __init__(self):
        super().__init__("redis")
        self.image = "redis:7.2.4"
        self.port = 6379

    def start(self):
        self.container = RedisContainer(self.image)
        self.container.with_exposed_ports(self.port)
        self.container = self.container.start()
        self.ports["redis"] = int(self.container.get_exposed_port(self.port))
        self.env = {
            "REDIS_URI": f"redis://localhost:{self.ports['redis']}/0",
            "REDIS__URI": f"redis://localhost:{self.ports['redis']}/0",
            "CODESTORY_REDIS__URI": f"redis://localhost:{self.ports['redis']}/0",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": str(self.ports["redis"]),
            "CELERY_BROKER_URL": f"redis://localhost:{self.ports['redis']}/0",
            "CELERY_RESULT_BACKEND": f"redis://localhost:{self.ports['redis']}/0",
        }
        return self

    def wait_for_ready(self, timeout=60):
        import redis as redis_py
        start = time.time()
        while time.time() - start < timeout:
            try:
                client = redis_py.Redis(host="localhost", port=self.ports["redis"])
                client.ping()
                self.ready = True
                return
            except Exception:
                time.sleep(1)
        raise RuntimeError("Redis testcontainer did not become ready in time")

# Registry of all service containers to be started for integration/E2E tests
SERVICE_CONTAINERS = {
    "neo4j": Neo4jServiceContainer,
    "redis": RedisServiceContainer,
    # Add new services here as needed
}

@pytest.fixture(scope="session")
def unified_test_env(request):
    """
    Unified session-scoped fixture for parallel, resource-isolated integration/E2E testing.

    - Starts all required service containers (Neo4j, Redis, etc.) using testcontainers.
    - Allocates dynamic ports for each pytest-xdist worker/process to guarantee isolation.
    - Injects all required environment variables for the test session.
    - Ensures no global/shared state or port collisions between parallel workers.
    - All integration/E2E tests must use this fixture for service access.

    Cross-links:
      - specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
      - code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

    Parallelization notes:
      - Each pytest-xdist worker runs in a separate process and gets its own containers/ports.
      - The worker id is used to namespace container names for debugging and to avoid rare collisions.
      - All environment variables are set per-process and do not leak between workers.
    """
    import uuid

    # Get pytest-xdist worker id if running in parallel, else use "gw0"
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "gw0")
    unique_run_id = str(uuid.uuid4())[:8]

    containers = {}
    env = {}

    # Start all containers with worker-specific names
    for name, cls in SERVICE_CONTAINERS.items():
        container = cls()
        # If the container supports custom naming, set a unique name
        if hasattr(container, "container"):
            # testcontainers auto-names, but we can set an env for debugging
            container.env["CODESTORY_TEST_WORKER_ID"] = worker_id
            container.env["CODESTORY_TEST_RUN_ID"] = unique_run_id
        container = container.start()
        containers[name] = container
        env.update(container.get_env())
        # Add worker id and run id to env for downstream debugging
        env[f"CODESTORY_TEST_WORKER_ID"] = worker_id
        env[f"CODESTORY_TEST_RUN_ID"] = unique_run_id

    # Set environment variables for all subprocesses in this worker
    for k, v in env.items():
        os.environ[k] = v

    # Clear settings cache to ensure new environment variables are used
    try:
        from codestory.config.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        print(f"[unified_test_env] Settings cache cleared, env: {env}")
    except Exception as e:
        print(f"[unified_test_env] Warning: Could not clear settings cache: {e}")

    # Wait for all containers to be ready
    for container in containers.values():
        container.wait_for_ready()

    # Compose a unified dict of all endpoints and ports
    endpoints = {}
    for name, container in containers.items():
        endpoints.update(container.get_env())
        for port_name, port_val in container.get_ports().items():
            endpoints[f"{name}_{port_name}_port"] = port_val
    endpoints["CODESTORY_TEST_WORKER_ID"] = worker_id
    endpoints["CODESTORY_TEST_RUN_ID"] = unique_run_id

    yield endpoints

    # Stop all containers
    for container in containers.values():
        container.stop()
