"""Settings module implementing layered configuration with precedence rules."""
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar
import tomli
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Neo4jSettings(BaseModel):
    """Neo4j database connection settings."""
    uri: str = Field(..., description='Neo4j connection URI')
    username: str = Field('neo4j', description='Neo4j username')
    password: SecretStr = Field(..., description='Neo4j password')
    database: str = Field('neo4j', description='Neo4j database name')
    connection_timeout: int = Field(30, description='Connection timeout in seconds')
    max_connection_pool_size: int = Field(50, description='Maximum connection pool size')
    connection_acquisition_timeout: int = Field(60, description='Connection acquisition timeout in seconds')

class RedisSettings(BaseModel):
    """Redis connection settings."""
    uri: str = Field(..., description='Redis connection URI')

class OpenAISettings(BaseModel):
    """OpenAI API settings."""
    api_key: SecretStr | None = Field(None, description='OpenAI API key (for direct API key auth)')
    endpoint: str = Field('https://api.openai.com/v1', description='OpenAI API endpoint')
    tenant_id: str | None = Field(None, description='Azure AD tenant ID for authentication')
    subscription_id: str | None = Field(None, description='Azure subscription ID')
    embedding_model: str = Field('text-embedding-3-small', description='OpenAI embedding model to use')
    chat_model: str = Field('gpt-4o', description='OpenAI chat model to use')
    reasoning_model: str = Field('gpt-4o', description='OpenAI model for reasoning tasks')
    api_version: str = Field('2025-03-01-preview', description='API version (for Azure OpenAI)')
    max_retries: int = Field(3, description='Maximum number of retries')
    retry_backoff_factor: float = Field(2.0, description='Backoff factor between retries')
    temperature: float = Field(0.1, description='Temperature for generation')
    max_tokens: int = Field(4096, description='Maximum tokens per request')
    timeout: float = Field(60.0, description='Timeout in seconds for API requests')

class AzureOpenAISettings(BaseModel):
    """Azure OpenAI API settings."""
    api_key: SecretStr | None = Field(None, description='Azure OpenAI API key')
    endpoint: str | None = Field(None, description='Azure OpenAI endpoint')
    deployment_id: str = Field('gpt-4o', description='Azure OpenAI deployment ID')
    api_version: str = Field('2024-05-01', description='Azure OpenAI API version')
    embedding_model: str = Field('text-embedding-3-small', description='Azure OpenAI embedding model to use')
    chat_model: str = Field('gpt-4o', description='Azure OpenAI chat model to use')
    reasoning_model: str = Field('gpt-4o', description='Azure OpenAI model for reasoning tasks')

class ServiceSettings(BaseModel):
    """Service configuration settings."""
    host: str = Field('0.0.0.0', description='Service host')
    port: int = Field(8000, description='Service port')
    workers: int = Field(4, description='Number of worker processes')
    log_level: str = Field('INFO', description='Logging level')
    enable_telemetry: bool = Field(True, description='Enable OpenTelemetry')
    worker_concurrency: int = Field(4, description='Celery worker concurrency')

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls: Any, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()

class IngestionSettings(BaseModel):
    """Ingestion pipeline settings."""
    config_path: str = Field('pipeline_config.yml', description='Path to pipeline configuration file')
    chunk_size: int = Field(1024, description='Text chunk size for processing')
    chunk_overlap: int = Field(200, description='Overlap between text chunks')
    embedding_model: str = Field('text-embedding-3-small', description='Model for embeddings')
    embedding_dimensions: int = Field(1536, description='Dimensions in embedding vectors')
    max_retries: int = Field(3, description='Number of retry attempts')
    retry_backoff_factor: float = Field(2.0, description='Backoff multiplier between retries')
    concurrency: int = Field(5, description='Default concurrency for ingestion tasks')
    resource_max_tokens: int = Field(4, description='Maximum number of concurrent ingestion resource tokens (for throttling)')
    steps: dict[str, dict[str, Any]] = Field(default_factory=dict, description='Step-specific configuration')

    @model_validator(mode='after')
    def ensure_default_steps(self: Any) -> 'IngestionSettings':
        """Ensure default steps configuration exists."""
        if 'steps' not in self.__dict__ or not self.steps:
            self.steps = {'blarify': {'timeout': 300, 'docker_image': 'codestory/blarify:latest'}, 'filesystem': {'ignore_patterns': ['node_modules/', '.git/', '__pycache__/']}, 'summarizer': {'max_concurrency': 5, 'max_tokens_per_file': 8000}, 'docgrapher': {'enabled': True}}
        return self

class PluginSettings(BaseModel):
    """Plugin settings."""
    enabled: list[str] = Field(['blarify', 'filesystem', 'summarizer', 'docgrapher'], description='List of enabled plugins')
    plugin_directory: str = Field('plugins', description='Directory for plugin discovery')

class TelemetrySettings(BaseModel):
    """Telemetry settings."""
    metrics_port: int = Field(9090, description='Port for Prometheus metrics')
    metrics_endpoint: str = Field('/metrics', description='Endpoint for Prometheus metrics')
    trace_sample_rate: float = Field(1.0, description='OpenTelemetry trace sample rate')
    log_format: str = Field('json', description='Log format')

    @field_validator('log_format')
    @classmethod
    def validate_log_format(cls: Any, v: str) -> str:
        """Validate that log format is either 'json' or 'text'."""
        if v not in ['json', 'text']:
            raise ValueError("log_format must be either 'json' or 'text'")
        return v

class InterfaceSettings(BaseModel):
    """Interface settings for GUI and CLI."""
    theme: str = Field('dark', description='Default theme (dark/light)')
    default_view: str = Field('graph', description='Default view (graph/list)')
    graph_layout: str = Field('force', description='Default graph layout algorithm')
    max_nodes: int = Field(1000, description='Maximum nodes to display at once')
    max_edges: int = Field(5000, description='Maximum edges to display at once')
    auto_refresh: bool = Field(True, description='Auto-refresh views')
    refresh_interval: int = Field(30, description='Refresh interval in seconds')

class AzureSettings(BaseModel):
    """Azure settings."""
    keyvault_name: str | None = Field(None, description='Azure KeyVault name')
    tenant_id: str | None = Field(None, description='Azure tenant ID')
    client_id: str | None = Field(None, description='Azure client ID')
    client_secret: SecretStr | None = Field(None, description='Azure client secret')

def get_project_root() -> Path:
    """Return the path to the project root directory."""
    return Path(__file__).parent.parent.parent.parent

class Settings(BaseSettings):
    """Main settings class with layered configuration.

    Loads settings with the following precedence:
    1. Environment variables
    2. .env file
    3. .codestory.toml
    4. Default values

    Environment variables are expected to be uppercase and can use double underscore
    as a separator for nested settings, e.g., NEO4J__PASSWORD for neo4j.password.
    """
    app_name: str = Field('code-story', description='Application name')
    version: str = Field('0.1.0', description='Application version')
    description: str = Field('A system to convert codebases into richly-linked knowledge graphs with natural-language summaries', description='Application description')
    environment: str = Field('development', description='Application environment')
    log_level: str = Field('INFO', description='Logging level')
    auth_enabled: bool = Field(False, description='Enable authentication')
    neo4j: Neo4jSettings
    redis: RedisSettings
    openai: OpenAISettings
    azure_openai: AzureOpenAISettings
    service: ServiceSettings
    ingestion: IngestionSettings
    plugins: PluginSettings
    telemetry: TelemetrySettings
    interface: InterfaceSettings
    azure: AzureSettings
    _CONFIG_FILE: ClassVar[str] = '.codestory.toml'
    _DEFAULT_CONFIG_FILE: ClassVar[str] = '.codestory.default.toml'
    _ENV_FILE: ClassVar[str] = '.env'
    model_config = SettingsConfigDict(env_prefix='CODESTORY_', env_file='.env', env_nested_delimiter='__', case_sensitive=False, extra='ignore', validate_default=True)

    def __init__(self: Any, **data: Any) -> None:
        """Initialize settings with layered configuration."""
        in_test_env = os.environ.get('CODESTORY_TEST_ENV') == 'true' or os.environ.get('NEO4J_DATABASE') == 'testdb' or 'pytest' in sys.modules or (os.environ.get('GITHUB_ACTIONS') == 'true')
        if in_test_env:
            print(f'Detected test environment. Current directory: {os.getcwd()}')
            print(f'Project root: {get_project_root()}')
        custom_config_file = os.environ.get('CODESTORY_CONFIG_FILE')
        toml_settings: dict[Any, Any] = {}
        config_files_to_try: list[Any] = []
        if in_test_env:
            test_config_paths = [os.path.join(get_project_root(), 'tests/fixtures/test_config.toml'), os.path.join(os.getcwd(), 'tests/fixtures/test_config.toml'), os.path.join(os.getcwd(), 'test_config.toml'), '/home/runner/work/code-story/code-story/tests/fixtures/test_config.toml']
            for test_path in test_config_paths:
                if os.path.exists(test_path):
                    config_files_to_try = [test_path]
                    print(f'Found test config at: {test_path}')
                    break
                else:
                    print(f'Test config not found at: {test_path}')
        else:
            if custom_config_file:
                config_files_to_try.append(custom_config_file)
            config_files_to_try.append(self._CONFIG_FILE)
            default_config_path = os.path.join(get_project_root(), self._DEFAULT_CONFIG_FILE)
            if os.path.exists(default_config_path):
                config_files_to_try.append(default_config_path)
        config_loaded = False
        for cf in config_files_to_try:
            if os.path.exists(cf):
                try:
                    with open(cf, 'rb') as f:
                        if in_test_env:
                            print(f'Loading TOML config from {cf}')
                        toml_data = tomli.load(f)
                        if in_test_env:
                            print(f"Config loaded, keys: {', '.join(toml_data.keys())}")
                        toml_settings = flatten_dict(toml_data)
                        if in_test_env:
                            print(f'Flattened settings created, length: {len(toml_settings)}')
                        config_loaded = True
                        break
                except Exception as e:
                    if in_test_env:
                        print(f'Error loading {cf}: {e}')
                        import traceback
                        traceback.print_exc()
        if not config_loaded and in_test_env:
            pass
        elif in_test_env:
            print('No test configuration found. Using default test settings.')
            toml_settings = {'app_name': 'code-story-test', 'version': '0.1.0', 'description': 'Test environment', 'environment': 'testing', 'log_level': 'DEBUG', 'auth_enabled': False, 'neo4j__uri': 'bolt://localhost:7687', 'neo4j__username': 'neo4j', 'neo4j__password': 'password', 'neo4j__database': 'testdb', 'neo4j__connection_timeout': 30, 'neo4j__max_connection_pool_size': 50, 'neo4j__connection_acquisition_timeout': 60, 'redis__uri': os.environ.get('REDIS__URI') or os.environ.get('REDIS_URI') or 'redis://localhost:6380/0', 'openai__api_key': 'sk-test-key-openai', 'openai__endpoint': 'https://api.openai.com/v1', 'openai__embedding_model': 'text-embedding-3-small', 'openai__chat_model': 'gpt-4o', 'openai__reasoning_model': 'gpt-4o', 'openai__api_version': '2025-03-01-preview', 'openai__max_retries': 3, 'openai__retry_backoff_factor': 2.0, 'openai__temperature': 0.1, 'openai__max_tokens': 4096, 'openai__timeout': 60.0, 'azure_openai__api_key': 'sk-test-key-azure', 'azure_openai__endpoint': '<your-endpoint>', 'azure_openai__deployment_id': 'gpt-4o', 'azure_openai__api_version': '2024-05-01', 'azure_openai__embedding_model': 'text-embedding-3-small', 'azure_openai__chat_model': 'gpt-4o', 'azure_openai__reasoning_model': 'gpt-4o', 'service__host': '0.0.0.0', 'service__port': 8000, 'service__workers': 4, 'service__log_level': 'INFO', 'service__enable_telemetry': True, 'service__worker_concurrency': 4, 'ingestion__config_path': 'pipeline_config.yml', 'ingestion__chunk_size': 1024, 'ingestion__chunk_overlap': 200, 'ingestion__embedding_model': 'text-embedding-3-small', 'ingestion__embedding_dimensions': 1536, 'ingestion__max_retries': 3, 'ingestion__retry_backoff_factor': 2.0, 'ingestion__concurrency': 5, 'ingestion__steps': {'blarify': {'timeout': 300, 'docker_image': 'codestory/blarify:latest'}, 'filesystem': {'ignore_patterns': ['node_modules/', '.git/', '__pycache__/']}, 'summarizer': {'max_concurrency': 5, 'max_tokens_per_file': 8000}, 'docgrapher': {'enabled': True}}, 'plugins__enabled': ['blarify', 'filesystem', 'summarizer', 'docgrapher'], 'plugins__plugin_directory': 'plugins', 'telemetry__metrics_port': 9090, 'telemetry__metrics_endpoint': '/metrics', 'telemetry__trace_sample_rate': 1.0, 'telemetry__log_format': 'json', 'interface__theme': 'dark', 'interface__default_view': 'graph', 'interface__graph_layout': 'force', 'interface__max_nodes': 1000, 'interface__max_edges': 5000, 'interface__auto_refresh': True, 'interface__refresh_interval': 30, 'azure__keyvault_name': '', 'azure__tenant_id': '', 'azure__client_id': '', 'azure__client_secret': ''}
        merged_settings = {**toml_settings, **data}
        if in_test_env:
            print(f"Merged settings keys: {', '.join(merged_settings.keys())}")
            print(f'Number of merged settings: {len(merged_settings)}')
        has_flattened = any(('__' in k for k in merged_settings))
        if has_flattened:
            if in_test_env:
                print('Detected flattened settings, converting to nested structure...')
            nested_settings = unflatten_dict(merged_settings)
            if in_test_env:
                print(f"Nested settings top-level keys: {', '.join(nested_settings.keys())}")
            required_fields = ['neo4j', 'redis', 'openai', 'azure_openai', 'service', 'ingestion', 'plugins', 'telemetry', 'interface', 'azure']
            for field in required_fields:
                if field not in nested_settings:
                    if in_test_env:
                        print(f'Adding missing required nested field: {field}')
                    nested_settings[field] = {}
            if in_test_env:
                print('Initializing with nested settings')
            super().__init__(**nested_settings)
            return
        if in_test_env:
            required_fields = ['neo4j', 'redis', 'openai', 'azure_openai', 'service', 'ingestion', 'plugins', 'telemetry', 'interface', 'azure']
            for field in required_fields:
                if not any((k.startswith(f'{field}__') or k == field for k in merged_settings)):
                    if in_test_env:
                        print(f'Adding missing required field: {field}')
                    merged_settings[field] = {}
        super().__init__(**merged_settings)
        self._load_secrets_from_keyvault()

    def _load_secrets_from_keyvault(self: Any) -> None:
        """Load sensitive settings from Azure KeyVault if configured."""
        if not self.azure.keyvault_name:
            return
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=f'https://{self.azure.keyvault_name}.vault.azure.net/', credential=credential)
            if not self.neo4j.password.get_secret_value():
                try:
                    secret = client.get_secret('neo4j-password')
                    self.neo4j.password = SecretStr(secret.value) if secret.value is not None else None
                except Exception:
                    pass
            if not self.openai.api_key.get_secret_value():
                try:
                    secret = client.get_secret('openai-api-key')
                    self.openai.api_key = SecretStr(secret.value) if secret.value is not None else None
                except Exception:
                    pass
            if self.azure_openai.api_key is None or not self.azure_openai.api_key.get_secret_value():
                try:
                    secret = client.get_secret('azure-openai-api-key')
                    self.azure_openai.api_key = SecretStr(secret.value) if secret.value is not None else None
                except Exception:
                    pass
            if self.azure.client_secret is None or not self.azure.client_secret.get_secret_value():
                try:
                    secret = client.get_secret('azure-client-secret')
                    self.azure.client_secret = SecretStr(secret.value) if secret.value is not None else None
                except Exception:
                    pass
        except ImportError:
            print('Azure SDK not installed. Skipping KeyVault integration.')
        except Exception as e:
            print(f'Error loading secrets from KeyVault: {e}')

def flatten_dict(d: dict[str, Any], parent_key: str='', sep: str='__') -> dict[str, Any]:
    """Flatten nested dictionary with separator in keys.

    Example:
        {"neo4j": {"uri": "bolt://localhost:7687"}} -> {"neo4j__uri": "bolt://localhost:7687"}
    """
    items: list[Any] = []
    for k, v in d.items():
        new_key = f'{parent_key}{sep}{k}' if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def unflatten_dict(d: dict[str, Any], sep: str='__') -> dict[str, Any]:
    """Unflatten a dictionary with separator in keys into nested dictionaries.

    Example:
        {"neo4j__uri": "bolt://localhost:7687"} -> {"neo4j": {"uri": "bolt://localhost:7687"}}
    """
    result: dict[Any, Any] = {}
    for key, value in d.items():
        parts = key.split(sep)
        if len(parts) == 1:
            result[key] = value
            continue
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result

@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance.

    This function creates a singleton instance of Settings that is cached
    for the life of the application.

    Returns:
        Settings: The global settings instance.
    """
    return Settings()

def refresh_settings() -> None:
    """Refresh the settings from all sources.

    This clears the cache and forces a reload of all settings.
    """
    get_settings.cache_clear()