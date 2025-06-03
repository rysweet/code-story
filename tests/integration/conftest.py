from typing import Any

"Pytest configuration for integration tests."
import glob
import os
import re
import sys
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

from .test_config import get_test_settings


def fix_neo4j_port_config() -> None:
    """Fix Neo4j URI syntax in test files."""
    print("Auto-fixing Neo4j port configuration in test files...")
    test_files = glob.glob("tests/**/*.py", recursive=True)
    fixed_count = 0
    for file_path in test_files:
        try:
            with open(file_path) as f:
                content = f.read()
            pattern1 = '"bolt://localhost:" \\+ \\(os\\.environ\\.get\\("CI"\\) == "true" and "7687" or "7688"\\)"'
            replacement1 = 'f"bolt://localhost:{neo4j_port}"'
            if re.search(pattern1, content):
                content = re.sub(pattern1, replacement1, content)
                if "neo4j_port = " not in content:
                    content = re.sub(
                        "import os",
                        'import os\n\n# Determine Neo4j port based on CI environment\nci_env = os.environ.get("CI") == "true"\nneo4j_port = "7687" if ci_env else "7688"',
                        content,
                    )
                with open(file_path, "w") as f:
                    f.write(content)
                print(f"Fixed {file_path}")
                fixed_count += 1
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
    if fixed_count > 0:
        print(f"Fixed {fixed_count} files.")
    else:
        print("No files needed fixing.")


if os.environ.get("CI") == "true":
    fix_neo4j_port_config()


def pytest_addoption(parser: Any) -> None:
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


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "neo4j: mark test as requiring Neo4j")
    config.addinivalue_line("markers", "celery: mark test as requiring Celery")


def pytest_collection_modifyitems(config: Any, items: Any) -> None:
    """Enable Neo4j and Celery tests by default.

    Neo4j and Redis are considered core components of the system, so their
    tests should run by default. Only Azure-dependent tests are skipped
    unless explicitly enabled.
    """
    skip_neo4j = pytest.mark.skip(
        reason="Tests using Neo4j are disabled with --skip-neo4j"
    )
    skip_celery = pytest.mark.skip(
        reason="Tests using Celery are disabled with --skip-celery"
    )
    if config.getoption("--skip-neo4j", False):
        for item in items:
            if "neo4j" in item.keywords:
                item.add_marker(skip_neo4j)
    if config.getoption("--skip-celery", False):
        for item in items:
            if "celery" in item.keywords:
                item.add_marker(skip_celery)


@pytest.fixture(scope="session", autouse=True)
def mock_settings() -> None:
    """Mock the settings module to use test settings.

    This fixture patches the get_settings function to return test settings
    for all integration tests.
    """
    with patch(
        "codestory.config.settings.get_settings", return_value=get_test_settings()
    ):
        yield


# Removed neo4j_env fixture: environment variables for Neo4j/Redis are now set by container fixtures.


# Removed load_env_vars fixture: environment variables for Neo4j/Redis are now set by container fixtures.


import socket
import time

@pytest.fixture
def neo4j_connector() -> None:
    """Return a Neo4j connector for tests, waiting for Bolt port to be ready."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    from urllib.parse import urlparse

    uri = os.environ.get("NEO4J__URI") or os.environ.get("NEO4J_URI")
    if not uri:
        raise RuntimeError("NEO4J_URI environment variable not set by container fixture")

    parsed = urlparse(uri)
    bolt_host = parsed.hostname
    bolt_port = parsed.port

    def wait_for_bolt(host: str, port: int, timeout: float = 60.0) -> None:
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection((host, port), timeout=2):
                    return
            except (OSError, ConnectionRefusedError):
                time.sleep(1)
        raise RuntimeError(f"Timed out waiting for Neo4j Bolt at {host}:{port}")

    username = (
        os.environ.get("NEO4J__USERNAME") or os.environ.get("NEO4J_USERNAME") or "neo4j"
    )
    password = (
        os.environ.get("NEO4J__PASSWORD")
        or os.environ.get("NEO4J_PASSWORD")
        or "password"
    )
    database = (
        os.environ.get("NEO4J__DATABASE") or os.environ.get("NEO4J_DATABASE") or "neo4j"
    )
    print(f"DEBUG: Using Neo4j database: {database}")
    wait_for_bolt(bolt_host, int(bolt_port))

    connector = Neo4jConnector(
        uri=uri, username=username, password=password, database=database
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
def redis_client() -> None:
    """Create a Redis client for testing and manage cleanup.

    This fixture provides a Redis client and ensures proper cleanup after tests.
    """
    import redis

    redis_uri = (
        os.environ.get("REDIS__URI")
        or os.environ.get("REDIS_URI")
        or os.getenv("REDIS_URI", "redis://localhost:6379/0")
    )
    os.environ["REDIS_URI"] = redis_uri
    os.environ["REDIS__URI"] = redis_uri
    print(f"DEBUG: Using Redis URI: {redis_uri}")
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
def celery_app(redis_client: Any) -> None:
    """Provide a Celery app configured for integration testing.

    This fixture depends on redis_client to ensure Redis is properly set up
    and cleaned up for tests.
    """
    import importlib

    from codestory.ingestion_pipeline.celery_app import app

    redis_uri = (
        os.environ.get("REDIS__URI")
        or os.environ.get("REDIS_URI")
        or os.getenv("REDIS_URI", "redis://localhost:6379/0")
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
    app.conf.update(task_always_eager=False)
