"""Settings module implementing layered configuration with precedence rules."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List, Literal, Optional, ClassVar

import tomli
from pydantic import BaseModel, Field, field_validator, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseModel):
    """Neo4j database connection settings."""

    uri: str = Field(..., description="Neo4j connection URI")
    username: str = Field("neo4j", description="Neo4j username")
    password: SecretStr = Field(..., description="Neo4j password")
    database: str = Field("neo4j", description="Neo4j database name")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    max_connection_pool_size: int = Field(
        50, description="Maximum connection pool size"
    )
    connection_acquisition_timeout: int = Field(
        60, description="Connection acquisition timeout in seconds"
    )


class RedisSettings(BaseModel):
    """Redis connection settings."""

    uri: str = Field(..., description="Redis connection URI")


class OpenAISettings(BaseModel):
    """OpenAI API settings."""

    api_key: Optional[SecretStr] = Field(
        None, description="OpenAI API key (for direct API key auth)"
    )
    endpoint: str = Field(
        "https://api.openai.com/v1", description="OpenAI API endpoint"
    )
    tenant_id: Optional[str] = Field(
        None, description="Azure AD tenant ID for authentication"
    )
    subscription_id: Optional[str] = Field(None, description="Azure subscription ID")
    embedding_model: str = Field(
        "text-embedding-3-small", description="OpenAI embedding model to use"
    )
    chat_model: str = Field("gpt-4o", description="OpenAI chat model to use")
    reasoning_model: str = Field(
        "gpt-4o", description="OpenAI model for reasoning tasks"
    )
    api_version: str = Field(
        "2025-03-01-preview", description="API version (for Azure OpenAI)"
    )
    max_retries: int = Field(3, description="Maximum number of retries")
    retry_backoff_factor: float = Field(
        2.0, description="Backoff factor between retries"
    )
    temperature: float = Field(0.1, description="Temperature for generation")
    max_tokens: int = Field(4096, description="Maximum tokens per request")
    timeout: float = Field(60.0, description="Timeout in seconds for API requests")


class AzureOpenAISettings(BaseModel):
    """Azure OpenAI API settings."""

    api_key: Optional[SecretStr] = Field(None, description="Azure OpenAI API key")
    endpoint: Optional[str] = Field(None, description="Azure OpenAI endpoint")
    deployment_id: str = Field("gpt-4o", description="Azure OpenAI deployment ID")
    api_version: str = Field("2024-05-01", description="Azure OpenAI API version")
    embedding_model: str = Field(
        "text-embedding-3-small", description="Azure OpenAI embedding model to use"
    )
    chat_model: str = Field("gpt-4o", description="Azure OpenAI chat model to use")
    reasoning_model: str = Field(
        "gpt-4o", description="Azure OpenAI model for reasoning tasks"
    )


class ServiceSettings(BaseModel):
    """Service configuration settings."""

    host: str = Field("0.0.0.0", description="Service host")
    port: int = Field(8000, description="Service port")
    workers: int = Field(4, description="Number of worker processes")
    log_level: str = Field("INFO", description="Logging level")
    environment: Literal["development", "testing", "production"] = Field(
        "development", description="Deployment environment"
    )
    enable_telemetry: bool = Field(True, description="Enable OpenTelemetry")
    worker_concurrency: int = Field(4, description="Celery worker concurrency")

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class IngestionSettings(BaseModel):
    """Ingestion pipeline settings."""

    config_path: str = Field(
        "pipeline_config.yml", description="Path to pipeline configuration file"
    )
    chunk_size: int = Field(1024, description="Text chunk size for processing")
    chunk_overlap: int = Field(200, description="Overlap between text chunks")
    embedding_model: str = Field(
        "text-embedding-3-small", description="Model for embeddings"
    )
    embedding_dimensions: int = Field(
        1536, description="Dimensions in embedding vectors"
    )
    max_retries: int = Field(3, description="Number of retry attempts")
    retry_backoff_factor: float = Field(
        2.0, description="Backoff multiplier between retries"
    )
    concurrency: int = Field(5, description="Default concurrency for ingestion tasks")
    steps: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Step-specific configuration"
    )

    @model_validator(mode="after")
    def ensure_default_steps(self) -> "IngestionSettings":
        """Ensure default steps configuration exists."""
        if "steps" not in self.__dict__ or not self.steps:
            self.steps = {
                "blarify": {"timeout": 300, "docker_image": "codestory/blarify:latest"},
                "filesystem": {
                    "ignore_patterns": ["node_modules/", ".git/", "__pycache__/"]
                },
                "summarizer": {"max_concurrency": 5, "max_tokens_per_file": 8000},
                "docgrapher": {"enabled": True},
            }
        return self


class PluginSettings(BaseModel):
    """Plugin settings."""

    enabled: List[str] = Field(
        ["blarify", "filesystem", "summarizer", "docgrapher"],
        description="List of enabled plugins",
    )
    plugin_directory: str = Field(
        "plugins", description="Directory for plugin discovery"
    )


class TelemetrySettings(BaseModel):
    """Telemetry settings."""

    metrics_port: int = Field(9090, description="Port for Prometheus metrics")
    metrics_endpoint: str = Field(
        "/metrics", description="Endpoint for Prometheus metrics"
    )
    trace_sample_rate: float = Field(1.0, description="OpenTelemetry trace sample rate")
    log_format: str = Field("json", description="Log format")

    @field_validator("log_format")
    def validate_log_format(cls, v: str) -> str:
        """Validate that log format is either 'json' or 'text'."""
        if v not in ["json", "text"]:
            raise ValueError("log_format must be either 'json' or 'text'")
        return v


class InterfaceSettings(BaseModel):
    """Interface settings for GUI and CLI."""

    theme: str = Field("dark", description="Default theme (dark/light)")
    default_view: str = Field("graph", description="Default view (graph/list)")
    graph_layout: str = Field("force", description="Default graph layout algorithm")
    max_nodes: int = Field(1000, description="Maximum nodes to display at once")
    max_edges: int = Field(5000, description="Maximum edges to display at once")
    auto_refresh: bool = Field(True, description="Auto-refresh views")
    refresh_interval: int = Field(30, description="Refresh interval in seconds")


class AzureSettings(BaseModel):
    """Azure settings."""

    keyvault_name: Optional[str] = Field(None, description="Azure KeyVault name")
    tenant_id: Optional[str] = Field(None, description="Azure tenant ID")
    client_id: Optional[str] = Field(None, description="Azure client ID")
    client_secret: Optional[SecretStr] = Field(None, description="Azure client secret")


def get_project_root() -> Path:
    """Return the path to the project root directory."""
    # This assumes the config module is at src/codestory/config/settings.py
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

    # Core settings
    app_name: str = Field("code-story", description="Application name")
    version: str = Field("0.1.0", description="Application version")
    description: str = Field(
        "A system to convert codebases into richly-linked knowledge graphs with natural-language summaries",
        description="Application description",
    )
    environment: Literal["development", "testing", "production"] = Field(
        "development", description="Deployment environment"
    )
    log_level: str = Field("INFO", description="Logging level")

    # Authentication
    auth_enabled: bool = Field(False, description="Enable authentication")

    # Component settings
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

    _CONFIG_FILE: ClassVar[str] = ".codestory.toml"
    _ENV_FILE: ClassVar[str] = ".env"

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    def __init__(self, **data: Any) -> None:
        """Initialize settings with layered configuration."""
        # Load settings from .codestory.toml if it exists
        toml_settings = {}
        if os.path.exists(self._CONFIG_FILE):
            try:
                with open(self._CONFIG_FILE, "rb") as f:
                    toml_data = tomli.load(f)
                    toml_settings = flatten_dict(toml_data)
            except Exception as e:
                print(f"Error loading {self._CONFIG_FILE}: {e}")

        # Merge settings, with environment variables taking precedence
        merged_settings = {**toml_settings, **data}

        super().__init__(**merged_settings)

        # Load secrets from KeyVault if configured
        # Always try to call _load_secrets_from_keyvault to ensure mock is called in tests
        self._load_secrets_from_keyvault()

    def _load_secrets_from_keyvault(self) -> None:
        """Load sensitive settings from Azure KeyVault if configured."""
        if not self.azure.keyvault_name:
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
            if not self.neo4j.password.get_secret_value():
                try:
                    secret = client.get_secret("neo4j-password")
                    self.neo4j.password = SecretStr(secret.value)
                except Exception:
                    pass

            # Load OpenAI API key if needed
            if not self.openai.api_key.get_secret_value():
                try:
                    secret = client.get_secret("openai-api-key")
                    self.openai.api_key = SecretStr(secret.value)
                except Exception:
                    pass

            # Load Azure OpenAI API key if needed
            if (
                self.azure_openai.api_key is None
                or not self.azure_openai.api_key.get_secret_value()
            ):
                try:
                    secret = client.get_secret("azure-openai-api-key")
                    self.azure_openai.api_key = SecretStr(secret.value)
                except Exception:
                    pass

            # Load Azure client secret if needed
            if (
                self.azure.client_secret is None
                or not self.azure.client_secret.get_secret_value()
            ):
                try:
                    secret = client.get_secret("azure-client-secret")
                    self.azure.client_secret = SecretStr(secret.value)
                except Exception:
                    pass

        except ImportError:
            print("Azure SDK not installed. Skipping KeyVault integration.")
        except Exception as e:
            print(f"Error loading secrets from KeyVault: {e}")


def flatten_dict(
    d: Dict[str, Any], parent_key: str = "", sep: str = "__"
) -> Dict[str, Any]:
    """Flatten nested dictionary with separator in keys.

    Example:
        {"neo4j": {"uri": "bolt://localhost:7687"}} -> {"neo4j__uri": "bolt://localhost:7687"}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@lru_cache()
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
