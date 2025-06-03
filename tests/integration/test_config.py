"""Integration test configuration and utilities.

This module provides configuration for the integration tests, including
test-specific settings overrides.
"""

import os

from codestory.config.settings import (
    AzureOpenAISettings,
    AzureSettings,
    IngestionSettings,
    InterfaceSettings,
    Neo4jSettings,
    OpenAISettings,
    PluginSettings,
    RedisSettings,
    ServiceSettings,
    Settings,
    TelemetrySettings,
)


def get_test_settings() -> Settings:
    """Return settings configured for integration tests.

    This function creates a Settings instance with appropriate
    configuration for integration tests.

    Returns:
        Settings: Test-configured settings instance
    """
    # Define neo4j test settings
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")

    neo4j = Neo4jSettings(  # type: ignore[call-arg]
        uri=neo4j_uri,
        username="neo4j",
        password="password",  # type: ignore[arg-type]
        database="neo4j",  # Match test DB name in docker-compose.test.yml
    )

    # Define redis test settings based on environment
    redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379/0")

    redis = RedisSettings(
        uri=redis_uri,
    )

    # Define OpenAI test settings
    openai = OpenAISettings(  # type: ignore[call-arg]
        api_key="sk-test-key-openai",  # Fake key for testing  # type: ignore[arg-type]
        endpoint="https://api.openai.com/v1",
        embedding_model="text-embedding-3-small",
        chat_model="gpt-4o",
        reasoning_model="gpt-4o",
    )

    # Define Azure OpenAI test settings
    azure_openai = AzureOpenAISettings(
        api_key="test-azure-key",  # Fake key for testing  # type: ignore[arg-type]
        endpoint="https://test-azure-endpoint.openai.azure.com",
        deployment_id="gpt-4o",
        api_version="2024-05-01",
        embedding_model="text-embedding-3-small",
        chat_model="gpt-4o",
        reasoning_model="gpt-4o",
    )

    # Define service test settings
    service = ServiceSettings(  # type: ignore[call-arg]
        host="127.0.0.1",
        port=8001,  # Different port for testing
        workers=1,
        log_level="DEBUG",
        environment="testing",
        enable_telemetry=False,
        worker_concurrency=1,
    )

    # Define ingestion test settings
    ingestion = IngestionSettings(  # type: ignore[call-arg]
        config_path="pipeline_config.yml",
        chunk_size=1024,
        chunk_overlap=200,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        max_retries=3,
        retry_backoff_factor=2.0,
        concurrency=1,  # Lower concurrency for testing
        steps={},
    )

    # Define plugins test settings
    plugins = PluginSettings(
        enabled=["filesystem"],  # Only enable the filesystem plugin for testing
        plugin_directory="plugins",
    )

    # Define telemetry test settings
    telemetry = TelemetrySettings(
        metrics_port=9091,  # Different port for testing
        metrics_endpoint="/metrics",
        trace_sample_rate=1.0,
        log_format="json",
    )

    # Define interface test settings
    interface = InterfaceSettings(
        theme="light",
        default_view="graph",
        graph_layout="force",
        max_nodes=100,  # Lower for testing
        max_edges=500,  # Lower for testing
        auto_refresh=False,  # Disable auto-refresh for testing
        refresh_interval=30,
    )

    # Define Azure test settings
    azure = AzureSettings(
        keyvault_name="test-key-vault",
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",  # type: ignore[arg-type]
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
