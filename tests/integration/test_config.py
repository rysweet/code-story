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
    # Determine the correct port based on environment
    ci_env = os.environ.get("CI") == "true"
    docker_env = os.environ.get("CODESTORY_IN_CONTAINER") == "true"
    neo4j_port = "7687" if ci_env else ("7689" if docker_env else "7688")
    
    # Determine URI based on environment
    if docker_env:
        # In Docker environment, use container service name
        neo4j_uri = "bolt://neo4j:7687"
    else:
        # Otherwise use localhost with mapped port
        neo4j_uri = f"bolt://localhost:{neo4j_port}"
    
    neo4j = Neo4jSettings(
        uri=neo4j_uri,
        username="neo4j",
        password="password",
        database="testdb",  # Match test DB name in docker-compose.test.yml
    )

    # Define redis test settings based on environment
    if docker_env:
        # In Docker environment, use container service name
        redis_uri = "redis://redis:6379/0"
    else:
        # Otherwise use localhost with mapped port
        redis_uri = "redis://localhost:6389/0"  # Port mapped in docker-compose.yml
    
    redis = RedisSettings(
        uri=redis_uri,
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
        port=8001,  # Different port for testing
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
