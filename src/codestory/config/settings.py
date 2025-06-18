"""
Settings module for Code Story: robust layered configuration loader.

Supports precedence:
1. Environment variables (including nested keys via double underscore, e.g., NEO4J__URI)
2. .env file (dotenv format)
3. Project TOML config file (e.g., .codestory.toml)
4. Hardcoded defaults in code

Provides type-safe, validated settings for all major components using Pydantic models.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import tomli
from pydantic import BaseModel, Field, SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource

# --- Pydantic models for each config section ---

class Neo4jSettings(BaseModel):
    uri: str = Field("bolt://localhost:7687", description="Neo4j connection URI")
    username: str = Field("neo4j", description="Neo4j username")
    password: Optional[SecretStr] = Field(None, description="Neo4j password")
    database: str = Field("neo4j", description="Neo4j database name")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    max_connection_pool_size: int = Field(50, description="Maximum size of the connection pool")

class RedisSettings(BaseModel):
    uri: str = Field("redis://localhost:6379", description="Redis connection URI")

class OpenAISettings(BaseModel):
    api_key: Optional[SecretStr] = Field(None, description="OpenAI API key")
    endpoint: str = Field("https://api.openai.com/v1", description="OpenAI API endpoint")
    embedding_model: str = Field("text-embedding-3-small", description="Embedding model")
    chat_model: str = Field("gpt-4o", description="Chat model")
    reasoning_model: str = Field("gpt-4o", description="Reasoning model")
    api_version: str = Field("2025-03-01-preview", description="API version")
    timeout: float = Field(60.0, description="Request timeout in seconds")
    max_retries: int = Field(5, description="Maximum number of retry attempts")
    retry_backoff_factor: float = Field(2.0, description="Multiplier for exponential backoff")
    tenant_id: Optional[str] = Field(None, description="Azure tenant ID")

class AzureOpenAISettings(BaseModel):
    api_key: Optional[SecretStr] = Field(None, description="Azure OpenAI API key")
    endpoint: Optional[str] = Field(None, description="Azure OpenAI endpoint")
    deployment_id: str = Field("gpt-4o", description="Deployment ID")
    api_version: str = Field("2024-05-01", description="API version")

class ServiceSettings(BaseModel):
    host: str = Field("0.0.0.0", description="Service host")
    port: int = Field(8000, description="Service port")
    workers: int = Field(4, description="Number of worker processes")
    log_level: str = Field("INFO", description="Logging level")
    worker_concurrency: int = Field(4, description="Celery worker concurrency")

class IngestionSettings(BaseModel):
    config_path: str = Field("pipeline_config.yml", description="Pipeline config file")
    chunk_size: int = Field(1024, description="Text chunk size")
    concurrency: int = Field(5, description="Default concurrency")

class PluginSettings(BaseModel):
    enabled: list[str] = Field(default_factory=lambda: ["blarify", "filesystem", "summarizer", "docgrapher"])
    plugin_directory: str = Field("plugins", description="Plugin directory")

class TelemetrySettings(BaseModel):
    metrics_port: int = Field(9090, description="Prometheus metrics port")
    metrics_endpoint: str = Field("/metrics", description="Metrics endpoint")
    trace_sample_rate: float = Field(1.0, description="Trace sample rate")
    log_format: str = Field("json", description="Log format")

class InterfaceSettings(BaseModel):
    theme: str = Field("dark", description="UI theme")
    default_view: str = Field("graph", description="Default view")

class AzureSettings(BaseModel):
    keyvault_name: Optional[str] = Field(None, description="Azure KeyVault name")
    tenant_id: Optional[str] = Field(None, description="Azure tenant ID")
    client_id: Optional[str] = Field(None, description="Azure client ID")
    client_secret: Optional[SecretStr] = Field(None, description="Azure client secret")

# --- Main Settings class ---

class Settings(BaseSettings):
    app_name: str = Field("code-story", description="Application name")
    version: str = Field("0.1.0", description="Application version")
    environment: str = Field("development", description="Environment")
    log_level: str = Field("INFO", description="Logging level")
    auth_enabled: bool = Field(False, description="Enable authentication")

    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)
    service: ServiceSettings = Field(default_factory=ServiceSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    interface: InterfaceSettings = Field(default_factory=InterfaceSettings)
    azure: AzureSettings = Field(default_factory=AzureSettings)

    _CONFIG_FILE: str = ".codestory.toml"

    model_config = SettingsConfigDict(
        env_prefix="CODESTORY_",
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        """Initialize settings with Azure OpenAI fallback logic and testdb override."""
        super().__init__(**kwargs)

        import os
        test_env = os.environ.get("CODESTORY_TEST_ENV", "").lower() == "true"
        deployment_mode_test = os.environ.get("DEPLOYMENT_MODE", "").lower() == "test"

        # NOTE: Do NOT auto-switch to "testdb" here; integration fixtures prepare
        # the default "neo4j" database.  Tests that need an alternate DB should set
        # NEO4J_DATABASE explicitly.

        if test_env:
            # In test environment, allow un-prefixed REDIS__URI to override Redis settings
            if os.environ.get("REDIS__URI"):
                self.redis.uri = os.environ["REDIS__URI"]
            return  # Skip Azure override logic in test environment

        # If Azure OpenAI variables are set, use them for OpenAI settings
        if os.environ.get("AZURE_OPENAI__ENDPOINT"):
            self.openai.endpoint = os.environ["AZURE_OPENAI__ENDPOINT"]
        if os.environ.get("AZURE_OPENAI__API_KEY"):
            from pydantic import SecretStr
            self.openai.api_key = SecretStr(os.environ["AZURE_OPENAI__API_KEY"])
        if os.environ.get("AZURE_OPENAI__API_VERSION"):
            self.openai.api_version = os.environ["AZURE_OPENAI__API_VERSION"]
        if os.environ.get("AZURE_OPENAI__DEPLOYMENT_ID"):
            # Use deployment ID for chat and reasoning models only
            deployment = os.environ["AZURE_OPENAI__DEPLOYMENT_ID"]
            self.openai.chat_model = deployment
            self.openai.reasoning_model = deployment
            # Do NOT override embedding_model here; let it be set by OPENAI__EMBEDDING_MODEL or default
        if os.environ.get("AZURE_TENANT_ID"):
            self.openai.tenant_id = os.environ["AZURE_TENANT_ID"]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize the order of settings sources."""
        # Custom TOML config source
        class TomlConfigSettingsSource(PydanticBaseSettingsSource):
            def get_field_value(self, field_info: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
                # Load TOML config if present
                # In test environment, use test config by default
                default_config = ".codestory.toml"
                if os.environ.get("CODESTORY_TEST_ENV") == "true":
                    default_config = "tests/fixtures/test_config.toml"
                
                config_file = os.environ.get("CODESTORY_CONFIG_FILE") or default_config
                toml_path = Path(config_file)
                
                if not toml_path.exists():
                    return None, field_name, False
                    
                try:
                    with open(toml_path, "rb") as f:
                        toml_data = tomli.load(f)
                except Exception:
                    return None, field_name, False
                
                # Flatten TOML data to handle nested fields
                def flatten(d, parent_key="", sep="__"):
                    items = []
                    for k, v in d.items():
                        new_key = f"{parent_key}{sep}{k}" if parent_key else k
                        if isinstance(v, dict):
                            items.extend(flatten(v, new_key, sep=sep).items())
                        else:
                            items.append((new_key, v))
                    return dict(items)
                
                flat_data = flatten(toml_data)
                
                # Check if field exists in TOML data
                if field_name in flat_data:
                    return flat_data[field_name], field_name, True
                    
                return None, field_name, False

            def prepare_field_value(self, field_name: str, value: Any, value_is_complex: bool) -> Any:
                return value

            def __call__(self) -> dict[str, Any]:
                d: dict[str, Any] = {}
                
                # Load TOML config if present
                # In test environment, use test config by default
                default_config = ".codestory.toml"
                if os.environ.get("CODESTORY_TEST_ENV") == "true":
                    default_config = "tests/fixtures/test_config.toml"
                
                config_file = os.environ.get("CODESTORY_CONFIG_FILE") or default_config
                toml_path = Path(config_file)
                
                if not toml_path.exists():
                    return d
                    
                try:
                    with open(toml_path, "rb") as f:
                        toml_data = tomli.load(f)
                except Exception as e:
                    return d
                
                # Return both the original nested structure AND flattened keys
                # This ensures nested objects get proper data while still supporting flat env-style keys
                def flatten(data, parent_key="", sep="__"):
                    items = []
                    for k, v in data.items():
                        new_key = f"{parent_key}{sep}{k}" if parent_key else k
                        if isinstance(v, dict):
                            items.extend(flatten(v, new_key, sep=sep).items())
                        else:
                            items.append((new_key, v))
                    return dict(items)
                
                result = dict(toml_data)  # Start with original nested structure
                result.update(flatten(toml_data))  # Add flattened keys for env compatibility
                return result

        toml_settings = TomlConfigSettingsSource(settings_cls)
        
        # TOML config should take precedence over environment variables
        return (
            init_settings,
            toml_settings,      # TOML first after init
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    def _load_secrets_from_keyvault(self) -> None:
        """Load sensitive settings from Azure KeyVault if configured."""
        if not hasattr(self, "azure") or not getattr(self.azure, "keyvault_name", None):
            return

        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            credential = DefaultAzureCredential()
            client = SecretClient(
                vault_url=f"https://{self.azure.keyvault_name}.vault.azure.net/",
                credential=credential,
            )

            # Load Neo4j password if needed
            if hasattr(self, "neo4j") and hasattr(self.neo4j, "password") and not self.neo4j.password:
                try:
                    secret = client.get_secret("neo4j-password")
                    self.neo4j.password = (
                        SecretStr(secret.value) if secret.value is not None else None
                    )
                except Exception:
                    pass

            # Load OpenAI API key if needed
            if hasattr(self, "openai") and hasattr(self.openai, "api_key") and not self.openai.api_key:
                try:
                    secret = client.get_secret("openai-api-key")
                    self.openai.api_key = (
                        SecretStr(secret.value) if secret.value is not None else None
                    )
                except Exception:
                    pass

            # Load Azure OpenAI API key if needed
            if hasattr(self, "azure_openai") and hasattr(self.azure_openai, "api_key") and not self.azure_openai.api_key:
                try:
                    secret = client.get_secret("azure-openai-api-key")
                    self.azure_openai.api_key = (
                        SecretStr(secret.value) if secret.value is not None else None
                    )
                except Exception:
                    pass

            # Load Azure client secret if needed
            if hasattr(self, "azure") and hasattr(self.azure, "client_secret") and not self.azure.client_secret:
                try:
                    secret = client.get_secret("azure-client-secret")
                    self.azure.client_secret = (
                        SecretStr(secret.value) if secret.value is not None else None
                    )
                except Exception:
                    pass

        except ImportError:
            print("Azure SDK not installed. Skipping KeyVault integration.")
        except Exception as e:
            print(f"Error loading secrets from KeyVault: {e}")

@lru_cache
def get_settings() -> Settings:
    return Settings()
def get_project_root() -> "Path":
    """Return the path to the project root directory."""
    # This assumes the config module is at src/codestory/config/settings.py
    from pathlib import Path
    return Path(__file__).parent.parent.parent.parent
def refresh_settings() -> None:
    """Refresh the settings from all sources.

    This clears the cache and forces a reload of all settings.
    """
    get_settings.cache_clear()