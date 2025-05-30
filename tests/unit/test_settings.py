from typing import Any
'Tests for settings module and a direct settings provider.\n\nThis module contains tests for the settings module and also provides\na direct settings provider for use in tests.\n'
import os
from unittest.mock import patch
from pydantic import SecretStr
from codestory.config.settings import AzureOpenAISettings, AzureSettings, IngestionSettings, InterfaceSettings, Neo4jSettings, OpenAISettings, PluginSettings, RedisSettings, ServiceSettings, Settings, TelemetrySettings

def create_test_settings() -> Any:
    """Create a fully-initialized settings object for tests."""
    neo4j = Neo4jSettings(uri='bolt://localhost:7687', username='neo4j', password='password', database='testdb')
    redis = RedisSettings(uri='redis://localhost:6379/0')
    openai = OpenAISettings(api_key=SecretStr('sk-test-key-openai'), endpoint='https://api.openai.com/v1', embedding_model='text-embedding-3-small', chat_model='gpt-4o', reasoning_model='gpt-4o')
    azure_openai = AzureOpenAISettings(api_key=SecretStr('test-azure-key'), endpoint='<your-endpoint>', deployment_id='gpt-4o', api_version='2024-05-01', embedding_model='text-embedding-3-small', chat_model='gpt-4o', reasoning_model='gpt-4o')
    service = ServiceSettings(host='127.0.0.1', port=8000, workers=1, log_level='DEBUG', enable_telemetry=False, worker_concurrency=1)
    ingestion = IngestionSettings(config_path='pipeline_config.yml', chunk_size=1024, chunk_overlap=200, embedding_model='text-embedding-3-small', embedding_dimensions=1536, max_retries=3, retry_backoff_factor=2.0, concurrency=1, steps={})
    plugins = PluginSettings(enabled=['filesystem'], plugin_directory='plugins')
    telemetry = TelemetrySettings(metrics_port=9090, metrics_endpoint='/metrics', trace_sample_rate=1.0, log_format='json')
    interface = InterfaceSettings(theme='light', default_view='graph', graph_layout='force', max_nodes=1000, max_edges=5000, auto_refresh=False, refresh_interval=30)
    azure = AzureSettings(keyvault_name='test-key-vault', tenant_id='test-tenant-id', client_id='test-client-id', client_secret=SecretStr('test-client-secret'))
    settings = Settings(app_name='code-story-test', version='0.1.0', description='Test environment', environment='testing', log_level='DEBUG', auth_enabled=False, neo4j=neo4j, redis=redis, openai=openai, azure_openai=azure_openai, service=service, ingestion=ingestion, plugins=plugins, telemetry=telemetry, interface=interface, azure=azure)
    return settings
test_settings = create_test_settings()

def setup_test_settings() -> Any:
    """Set up test settings for unit tests."""
    settings_patch = patch('codestory.config.settings.get_settings', return_value=test_settings)
    settings_patch.start()
    new_patch = patch('codestory.config.settings.Settings.__new__', return_value=test_settings)
    new_patch.start()
    os.environ['CODESTORY_TEST_ENV'] = 'true'
    os.environ['NEO4J_DATABASE'] = 'testdb'
    return (settings_patch, new_patch)

def test_settings_creation() -> None:
    """Test that test settings can be created without errors."""
    settings = create_test_settings()
    assert settings is not None
    assert settings.neo4j is not None
    assert settings.neo4j.uri == 'bolt://localhost:7687'
    assert settings.neo4j.database == 'testdb'
    assert settings.redis is not None
    assert settings.redis.uri == 'redis://localhost:6379/0'
    assert settings.openai is not None
    assert settings.openai.api_key.get_secret_value() == 'sk-test-key-openai'
    assert settings.environment == 'testing'