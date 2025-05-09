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
        "--run-neo4j",
        action="store_true",
        default=False,
        help="Run tests that require Neo4j"
    )
    parser.addoption(
        "--run-celery",
        action="store_true",
        default=False,
        help="Run tests that require Celery"
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "neo4j: mark test as requiring Neo4j")
    config.addinivalue_line("markers", "celery: mark test as requiring Celery")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly enabled."""
    skip_neo4j = pytest.mark.skip(reason="Need --run-neo4j option to run")
    skip_celery = pytest.mark.skip(reason="Need --run-celery option to run")
    
    # Skip Neo4j tests
    if not config.getoption("--run-neo4j"):
        for item in items:
            if "neo4j" in item.keywords:
                item.add_marker(skip_neo4j)
    
    # Skip Celery tests
    if not config.getoption("--run-celery"):
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
    with patch('codestory.config.settings.get_settings', return_value=get_test_settings()):
        # Apply the patch for all tests
        yield


@pytest.fixture(scope="session", autouse=True)
def load_env_vars():
    """Load environment variables for integration tests.

    This fixture automatically loads environment variables from .env file
    and ensures that the Neo4j connection settings are available for tests.
    """
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    load_dotenv(env_path)

    # Ensure src directory is in Python path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    src_dir = os.path.join(project_root, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Set default Neo4j test variables if not already set
    # The setup_test_db.sh script should set these, but this is a fallback
    if "NEO4J_URI" not in os.environ:
        os.environ["NEO4J_URI"] = "bolt://localhost:7688"
    if "NEO4J_USERNAME" not in os.environ:
        os.environ["NEO4J_USERNAME"] = "neo4j"
    if "NEO4J_PASSWORD" not in os.environ:
        os.environ["NEO4J_PASSWORD"] = "password"
    if "NEO4J_DATABASE" not in os.environ:
        os.environ["NEO4J_DATABASE"] = "codestory-test"

    # Override the NEO4J__URI in environment to match the test container port
    os.environ["NEO4J__URI"] = "bolt://localhost:7688"

    # Set default Redis variables if not already set
    if "REDIS_URI" not in os.environ:
        os.environ["REDIS_URI"] = "redis://localhost:6379/0"


@pytest.fixture(scope="session")
def celery_config():
    """Configure Celery for testing."""
    return {
        'broker_url': 'memory://',
        'result_backend': 'rpc://',
        'task_always_eager': True,  # Tasks run synchronously in tests
        'task_eager_propagates': True,  # Exceptions are propagated
        'task_ignore_result': False,  # Results are tracked
        'worker_concurrency': 1,  # Single worker for tests
        'worker_prefetch_multiplier': 1,
        'task_acks_late': False,
        'task_track_started': True,
    }


@pytest.fixture(scope="session")
def celery_app():
    """Provide the Celery app for testing."""
    from codestory.ingestion_pipeline.celery_app import app
    # Configure app for testing
    app.conf.update(
        broker_url='memory://',
        result_backend='rpc://',
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