"""Pytest configuration for integration tests."""

import os
import pytest
from typing import Dict, Any

from dotenv import load_dotenv


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
def load_env_vars():
    """Load environment variables for integration tests.
    
    This fixture automatically loads environment variables from .env file
    and ensures that the Neo4j connection settings are available for tests.
    """
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    load_dotenv(env_path)
    
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
        
    # Set default Redis variables if not already set
    if "REDIS_URI" not in os.environ:
        os.environ["REDIS_URI"] = "redis://localhost:6379/0"