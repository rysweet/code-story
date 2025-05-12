"""Pytest configuration for unit tests."""

import os
import pytest
import sys
from unittest.mock import patch
from typing import Dict, Any

from dotenv import load_dotenv
from codestory.config.settings import (
    Settings,
    Neo4jSettings,
    RedisSettings,
    OpenAISettings,
    AzureOpenAISettings,
    ServiceSettings,
    IngestionSettings,
    PluginSettings,
    TelemetrySettings,
    InterfaceSettings,
    AzureSettings,
)


def get_test_settings() -> Settings:
    """Return settings configured for unit tests."""
    # Define neo4j test settings
    neo4j = Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password",
        database="codestory-test",
    )

    # Define redis test settings
    redis = RedisSettings(
        uri="redis://localhost:6379/0",
    )

    # Define OpenAI test settings
    openai = OpenAISettings(
        api_key="sk-test-key-openai",  # Fake key for testing
        endpoint="https://api.openai.com/v1",
        embedding_model="text-embedding-3-small",
        chat_model="gpt-4o",
        reasoning_model="gpt-4o",
    )

    # Define Azure OpenAI test settings
    azure_openai = AzureOpenAISettings(
        api_key="test-azure-key",  # Fake key for testing
        endpoint="https://test-azure-endpoint.openai.azure.com",
        deployment_id="gpt-4o",
        api_version="2024-05-01",
        embedding_model="text-embedding-3-small",
        chat_model="gpt-4o",
        reasoning_model="gpt-4o",
    )

    # Define service test settings
    service = ServiceSettings(
        host="127.0.0.1",
        port=8000,
        workers=1,
        log_level="DEBUG",
        environment="testing",
        enable_telemetry=False,
        worker_concurrency=1,
    )

    # Define ingestion test settings
    ingestion = IngestionSettings(
        config_path="pipeline_config.yml",
        chunk_size=1024,
        chunk_overlap=200,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        max_retries=3,
        retry_backoff_factor=2.0,
        concurrency=1,
        steps={},
    )

    # Define plugins test settings
    plugins = PluginSettings(
        enabled=["filesystem"],
        plugin_directory="plugins",
    )

    # Define telemetry test settings
    telemetry = TelemetrySettings(
        metrics_port=9090,
        metrics_endpoint="/metrics",
        trace_sample_rate=1.0,
        log_format="json",
    )

    # Define interface test settings
    interface = InterfaceSettings(
        theme="light",
        default_view="graph",
        graph_layout="force",
        max_nodes=1000,
        max_edges=5000,
        auto_refresh=False,
        refresh_interval=30,
    )

    # Define Azure test settings
    azure = AzureSettings(
        keyvault_name="test-key-vault",
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )

    # Create test settings instance
    settings = Settings(
        neo4j=neo4j,
        redis=redis,
        openai=openai,
        azure_openai=azure_openai,
        service=service,
        ingestion=ingestion,
        plugins=plugins,
        telemetry=telemetry,
        interface=interface,
        azure=azure,
    )

    return settings


@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """Mock the settings module to use test settings for all unit tests."""
    # Patch the get_settings function at module import time
    # This is critical since some modules import and call get_settings() during module loading

    # Import the module first to ensure it exists before patching
    from codestory.config.settings import get_settings as original_get_settings

    # Create and directly assign the test settings instance
    test_settings = get_test_settings()

    # Use more aggressive patching that affects existing imports
    with patch("codestory.config.settings.Settings.__init__", return_value=None):
        with patch("codestory.config.settings.Settings.__new__", return_value=test_settings):
            with patch("codestory.config.settings.get_settings", return_value=test_settings):
                # Apply the patch for all tests
                yield


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
    os.environ["NEO4J_DATABASE"] = "codestory-test"

    # Double underscore format for Pydantic nested settings
    os.environ["NEO4J__URI"] = "bolt://localhost:7687"
    os.environ["NEO4J__USERNAME"] = "neo4j"
    os.environ["NEO4J__PASSWORD"] = "password"
    os.environ["NEO4J__DATABASE"] = "codestory-test"

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
    os.environ["PLUGINS__ENABLED"] = "filesystem"

    # Telemetry settings
    os.environ["TELEMETRY__METRICS_PORT"] = "9090"

    # Interface settings
    os.environ["INTERFACE__THEME"] = "light"

    # Azure settings
    os.environ["AZURE__KEYVAULT_NAME"] = "test-key-vault"


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