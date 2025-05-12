"""Pytest configuration for integration tests."""

import os
import pytest
import sys
from unittest.mock import patch
from typing import Dict, Any

from dotenv import load_dotenv
from .test_config import get_test_settings


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
    # Keep old options for backward compatibility
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
    """Enable Neo4j and Celery tests by default.

    Neo4j and Redis are considered core components of the system, so their
    tests should run by default. Only Azure-dependent tests are skipped
    unless explicitly enabled.
    """
    # Neo4j and Celery tests are now enabled by default
    # They can be disabled with --skip-neo4j and --skip-celery options
    skip_neo4j = pytest.mark.skip(reason="Tests using Neo4j are disabled with --skip-neo4j")
    skip_celery = pytest.mark.skip(reason="Tests using Celery are disabled with --skip-celery")

    # Skip Neo4j tests if explicitly disabled
    if config.getoption("--skip-neo4j", False):
        for item in items:
            if "neo4j" in item.keywords:
                item.add_marker(skip_neo4j)

    # Skip Celery tests if explicitly disabled
    if config.getoption("--skip-celery", False):
        for item in items:
            if "celery" in item.keywords:
                item.add_marker(skip_celery)


@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """Mock the settings module to use test settings.

    This fixture patches the get_settings function to return test settings
    for all integration tests.
    """
    # We need to mock get_settings() to return test settings for integration tests
    from codestory.config.settings import get_settings as original_get_settings

    # Create a patch for the get_settings function
    with patch(
        "codestory.config.settings.get_settings", return_value=get_test_settings()
    ):
        # Apply the patch for all tests
        yield


@pytest.fixture(scope="session", autouse=True)
def load_env_vars():
    """Load environment variables for integration tests.

    This fixture automatically loads environment variables from .env file
    and ensures that the Neo4j connection settings are available for tests.
    """
    # Load environment variables from .env file
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
    )
    load_dotenv(env_path)

    # Ensure project root is in Python path for proper imports
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Set default Neo4j test variables
    os.environ["NEO4J_URI"] = "bolt://localhost:7688"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "codestory-test"

    # Set Neo4j settings for the code-story app via double-underscore format
    os.environ["NEO4J__URI"] = "bolt://localhost:7688"
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "codestory-test"

    # Set Redis settings
    # Test Redis runs on port 6380 instead of 6379 to avoid conflicts
    os.environ["REDIS_URI"] = "redis://localhost:6380/0"
    os.environ["REDIS__URI"] = "redis://localhost:6380/0"


@pytest.fixture(scope="session")
def celery_config(request):
    """Configure Celery for testing.

    This provides a different configuration based on whether we're running
    with --run-celery (using real Celery) or not (using in-memory tasks).
    """
    # Check if we're running with the real Celery flag
    using_real_celery = request.config.getoption("--run-celery")

    if using_real_celery:
        # For integration tests with real Celery
        return {
            # Use the Redis broker from test settings
            "broker_url": "redis://localhost:6380/0",
            "result_backend": "redis://localhost:6380/0",
            "task_always_eager": False,  # Tasks run asynchronously in real Celery
            "task_eager_propagates": False,
            "task_ignore_result": False,  # Results are tracked
            "worker_concurrency": 1,  # Single worker for tests
            "worker_prefetch_multiplier": 1,
            "task_acks_late": False,
            "task_track_started": True,
        }
    else:
        # For unit tests without real Celery
        return {
            "broker_url": "memory://",
            "result_backend": "rpc://",
            "task_always_eager": True,  # Tasks run synchronously in tests
            "task_eager_propagates": True,  # Exceptions are propagated
            "task_ignore_result": False,  # Results are tracked
            "worker_concurrency": 1,  # Single worker for tests
            "worker_prefetch_multiplier": 1,
            "task_acks_late": False,
            "task_track_started": True,
        }


@pytest.fixture(scope="session")
def celery_app(request):
    """Provide the Celery app for testing.

    This provides a different configuration based on whether we're running
    with --run-celery (using real Celery) or not (using in-memory tasks).
    """
    from codestory.ingestion_pipeline.celery_app import app

    # Check if we're running with the real Celery flag
    using_real_celery = request.config.getoption("--run-celery")

    if using_real_celery:
        # For integration tests with real Celery, don't modify the app
        # The app will use the Redis settings from the test environment
        return app
    else:
        # For unit tests without real Celery
        app.conf.update(
            broker_url="memory://",
            result_backend="rpc://",
            task_always_eager=True,  # Tasks run synchronously in tests
            task_eager_propagates=True,  # Exceptions are propagated
            task_ignore_result=False,  # Results are tracked
            worker_concurrency=1,  # Single worker for tests
            worker_prefetch_multiplier=1,
            task_acks_late=False,
            task_track_started=True,
        )
        return app


@pytest.fixture(scope="function")
def neo4j_connector():
    """Create a Neo4j connector for testing."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector

    # Use direct connection parameters to connect to the test Neo4j instance
    connector = Neo4jConnector(
        uri="bolt://localhost:7688",  # Port defined in docker-compose.test.yml
        username="neo4j",
        password="password",
        database="codestory-test",  # Database defined in docker-compose.test.yml
    )

    # Clear the database before each test - this is a WRITE operation
    try:
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True, params={})
        print("Successfully connected to Neo4j and cleared the database")
    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j: {str(e)}")

    yield connector

    # Close the connection
    connector.close()
