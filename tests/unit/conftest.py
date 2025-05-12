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
    # We need to mock get_settings() to return test settings for unit tests
    from codestory.config.settings import get_settings as original_get_settings

    # Create a patch for the get_settings function
    with patch("codestory.config.settings.get_settings", return_value=get_test_settings()):
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

    # Set basic environment variables for tests
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "codestory-test"

    # Set Redis settings
    os.environ["REDIS_URI"] = "redis://localhost:6379/0"
    
    # Set OpenAI mock credentials
    os.environ["OPENAI_API_KEY"] = "sk-test-key-openai"


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