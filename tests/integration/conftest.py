"""Pytest configuration for integration tests."""

import os
import pytest
import sys
import re
import glob
from unittest.mock import patch
from typing import Dict, Any

from dotenv import load_dotenv
from .test_config import get_test_settings

# Auto-fix Neo4j port configuration in test files
def fix_neo4j_port_config():
    """Fix Neo4j URI syntax in test files."""
    print("Auto-fixing Neo4j port configuration in test files...")
    test_files = glob.glob('tests/**/*.py', recursive=True)
    fixed_count = 0
    
    for file_path in test_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Fix syntax error with port configuration
            pattern1 = r'"bolt://localhost:" \+ \(os\.environ\.get\("CI"\) == "true" and "7687" or "7688"\)"'
            replacement1 = 'f"bolt://localhost:{neo4j_port}"'
            
            if re.search(pattern1, content):
                # Add port variable before the problematic line
                content = re.sub(
                    pattern1,
                    replacement1,
                    content
                )
                
                # Add port variable declaration if not already present
                if "neo4j_port = " not in content:
                    content = re.sub(
                        r'import os',
                        'import os\n\n# Determine Neo4j port based on CI environment\nci_env = os.environ.get("CI") == "true"\nneo4j_port = "7687" if ci_env else "7688"',
                        content
                    )
                
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"Fixed {file_path}")
                fixed_count += 1
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
    
    if fixed_count > 0:
        print(f"Fixed {fixed_count} files.")
    else:
        print("No files needed fixing.")

# Run the auto-fix at import time in CI environment
if os.environ.get("CI") == "true":
    fix_neo4j_port_config()


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


@pytest.fixture(scope="session")
def neo4j_env():
    """Setup Neo4j environment variables for tests."""
    # Determine the correct Neo4j port to use
    # In CI environment, Neo4j is often on the standard port
    # In local docker-compose.test.yml, it's on port 7688
    ci_env = os.environ.get("CI") == "true"
    neo4j_port = "7687" if ci_env else "7688"
    
    # Set the environment variables
    neo4j_uri = f"bolt://localhost:{neo4j_port}"
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["NEO4J__URI"] = neo4j_uri
    
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "testdb"
    
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "testdb"


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

    # Set up Neo4j environment variables (replicate neo4j_env fixture logic to avoid calling it directly)
    ci_env = os.environ.get("CI") == "true"
    neo4j_port = "7687" if ci_env else "7688"
    
    # Set the environment variables
    neo4j_uri = f"bolt://localhost:{neo4j_port}"
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["NEO4J__URI"] = neo4j_uri
    
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "testdb"
    
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "testdb"

    # Set Redis environment variables
    os.environ["REDIS_URI"] = "redis://localhost:6379/0"
    os.environ["REDIS__URI"] = "redis://localhost:6379/0"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"

    # Set OpenAI environment variables for testing
    os.environ["OPENAI_API_KEY"] = "sk-test-key-openai"
    os.environ["OPENAI__API_KEY"] = "sk-test-key-openai"


@pytest.fixture
def neo4j_connector():
    """Return a Neo4j connector for tests."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector

    # Get Neo4j connection details from environment variables
    # with fallback to default test values
    username = os.environ.get("NEO4J__USERNAME") or os.environ.get("NEO4J_USERNAME") or "neo4j"
    
    # Use correct Neo4j port based on environment
    ci_env = os.environ.get("CI") == "true"
    default_uri = f"bolt://localhost:{7687 if ci_env else 7688}"
    uri = os.environ.get("NEO4J__URI") or os.environ.get("NEO4J_URI") or default_uri
    password = os.environ.get("NEO4J__PASSWORD") or os.environ.get("NEO4J_PASSWORD") or "password"
    database = os.environ.get("NEO4J__DATABASE") or os.environ.get("NEO4J_DATABASE") or "testdb"

    # Create a Neo4j connector
    connector = Neo4jConnector(
        uri=uri,
        username=username,
        password=password,
        database=database,
    )

    yield connector

    # Clean up the connector
    connector.close()


@pytest.fixture(scope="function")
def celery_app():
    """Provide a Celery app configured for integration testing."""
    from codestory.ingestion_pipeline.celery_app import app

    # Configure Celery for testing with in-memory broker
    app.conf.update(
        broker_url="memory://",
        result_backend="rpc://",
        task_always_eager=True,  # Tasks run synchronously in tests
        task_eager_propagates=True,  # Exceptions are propagated
        task_ignore_result=False,  # Results are tracked
    )
    return app