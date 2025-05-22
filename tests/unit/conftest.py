"""Pytest configuration for unit tests."""

import os
import sys

import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """Mock the settings module to use test settings for all unit tests."""
    # Import the test settings module to setup test settings
    # Override required methods for correct behavior in tests
    from unittest.mock import MagicMock

    from tests.unit.test_settings import setup_test_settings, test_settings

    # Ensure any attribute lookup returns a mock object
    def getattr_mock(instance, name):
        if name in instance.__dict__:
            return instance.__dict__[name]
        return MagicMock()

    # Apply the patch to __getattr__ to handle nested attribute access
    test_settings.__getattr__ = lambda name: getattr_mock(test_settings, name)

    # Apply the patches
    patches = setup_test_settings()

    # Patch at every level to make sure it's used everywhere
    import importlib

    from codestory.config import settings as settings_module

    # Force reload the module to ensure patches take effect
    importlib.reload(settings_module)

    try:
        # Apply the patch for all tests
        yield test_settings
    finally:
        # Stop the patches when tests are done
        for p in patches:
            p.stop()


@pytest.fixture(scope="session", autouse=True)
def load_env_vars():
    """Load environment variables for unit tests."""
    # Load environment variables from .env file
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
    )
    load_dotenv(env_path)

    # Ensure project root is in Python path for proper imports
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Set all required environment variables in both formats for Pydantic BaseSettings

    # Neo4j settings
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "testdb"

    # Double underscore format for Pydantic nested settings
    os.environ["NEO4J__URI"] = "bolt://localhost:7687"
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "testdb"

    # Redis settings
    os.environ["REDIS_URI"] = "redis://localhost:6379/0"
    os.environ["REDIS__URI"] = "redis://localhost:6379/0"

    # OpenAI settings
    os.environ["OPENAI_API_KEY"] = "sk-test-key-openai"
    os.environ["OPENAI__API_KEY"] = "sk-test-key-openai"
    os.environ["OPENAI__EMBEDDING_MODEL"] = "text-embedding-3-small"
    os.environ["OPENAI__CHAT_MODEL"] = "gpt-4o"
    os.environ["OPENAI__REASONING_MODEL"] = "gpt-4o"

    # Azure OpenAI settings
    os.environ["AZURE_OPENAI__API_KEY"] = "test-azure-key"
    os.environ["AZURE_OPENAI__ENDPOINT"] = "https://test-azure-endpoint.openai.azure.com"
    os.environ["AZURE_OPENAI__DEPLOYMENT_ID"] = "gpt-4o"

    # Service settings
    os.environ["SERVICE__HOST"] = "127.0.0.1"
    os.environ["SERVICE__PORT"] = "8000"
    os.environ["SERVICE__ENVIRONMENT"] = "testing"

    # Ingestion settings
    os.environ["INGESTION__CONFIG_PATH"] = "pipeline_config.yml"

    # Plugins settings
    os.environ["PLUGINS__ENABLED"] = '["filesystem"]'

    # Telemetry settings
    os.environ["TELEMETRY__METRICS_PORT"] = "9090"

    # Interface settings
    os.environ["INTERFACE__THEME"] = "light"

    # Azure settings
    os.environ["AZURE__KEYVAULT_NAME"] = "test-key-vault"

    # Mark as test environment
    os.environ["CODESTORY_TEST_ENV"] = "true"


@pytest.fixture(scope="function")
def celery_config():
    """Configure Celery for testing."""
    return {
        "broker_url": "memory://",
        "result_backend": "rpc://",
        "task_always_eager": True,  # Tasks run synchronously in tests
        "task_eager_propagates": True,  # Exceptions are propagated
        "task_ignore_result": False,  # Results are tracked
    }


@pytest.fixture(scope="function")
def celery_app():
    """Provide a Celery app configured for unit testing."""
    from codestory.ingestion_pipeline.celery_app import app

    app.conf.update(
        broker_url="memory://",
        result_backend="rpc://",
        task_always_eager=True,
        task_eager_propagates=True,
        task_ignore_result=False,
    )
    return app