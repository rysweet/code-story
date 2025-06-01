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


@pytest.fixture(scope="session")
def neo4j_env() -> None:
    """Setup Neo4j environment variables for tests."""
    ci_env = os.environ.get("CI") == "true"
    docker_env = os.environ.get("CODESTORY_IN_CONTAINER") == "true"
    neo4j_port = "7687" if ci_env else "7689" if docker_env else "7688"
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
    os.environ["NEO4J_DATABASE"] = "testdb"
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "testdb"
    os.environ["REDIS_URI"] = redis_uri
    os.environ["REDIS__URI"] = redis_uri
    os.environ["REDIS_HOST"] = redis_host
    os.environ["REDIS_PORT"] = redis_port
    os.environ["CELERY_BROKER_URL"] = redis_uri
    os.environ["CELERY_RESULT_BACKEND"] = redis_uri


@pytest.fixture(scope="session", autouse=True)
def load_env_vars() -> None:
    """Load environment variables for integration tests.

    This fixture automatically loads environment variables from .env file
    and ensures that the Neo4j connection settings are available for tests.
    """
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
    )
    load_dotenv(env_path)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    ci_env = os.environ.get("CI") == "true"
    docker_env = os.environ.get("CODESTORY_IN_CONTAINER") == "true"
    neo4j_port = "7687" if ci_env else "7689" if docker_env else "7688"
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
    os.environ["NEO4J_DATABASE"] = "testdb"
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "testdb"
    os.environ["REDIS_URI"] = redis_uri
    os.environ["REDIS__URI"] = redis_uri
    os.environ["REDIS_HOST"] = redis_host
    os.environ["REDIS_PORT"] = redis_port
    os.environ["CELERY_BROKER_URL"] = redis_uri
    os.environ["CELERY_RESULT_BACKEND"] = redis_uri
    os.environ["OPENAI_API_KEY"] = "sk-test-key-openai"
    os.environ["OPENAI__API_KEY"] = "sk-test-key-openai"


@pytest.fixture
def neo4j_connector() -> None:
    """Return a Neo4j connector for tests."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector

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
    ci_env = os.environ.get("CI") == "true"
    docker_env = os.environ.get("CODESTORY_IN_CONTAINER") == "true"
    if docker_env:
        default_uri = "bolt://neo4j:7687"
    else:
        neo4j_port = "7687" if ci_env else "7688"
        default_uri = f"bolt://localhost:{neo4j_port}"
    uri = os.environ.get("NEO4J__URI") or os.environ.get("NEO4J_URI") or default_uri
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
        or "redis://localhost:6380/0"
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
        or "redis://localhost:6380/0"
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
