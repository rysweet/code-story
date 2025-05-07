"""Settings module implementing layered configuration with precedence rules."""

import os
from functools import lru_cache
from typing import Dict, List, Optional

import tomli
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseModel):
    """Neo4j database connection settings."""

    uri: str = Field(..., description="Neo4j connection URI")
    user: str = Field(..., description="Neo4j username")
    password: str = Field(..., description="Neo4j password")
    database: str = Field("neo4j", description="Neo4j database name")


class RedisSettings(BaseModel):
    """Redis connection settings."""

    uri: str = Field(..., description="Redis connection URI")


class OpenAISettings(BaseModel):
    """OpenAI API settings."""

    api_key: str = Field(..., description="OpenAI API key")
    model: str = Field("gpt-4o-2024-05-13", description="OpenAI model to use")
    temperature: float = Field(0.1, description="Temperature for generation")
    max_tokens: int = Field(4096, description="Maximum tokens per request")


class AzureOpenAISettings(BaseModel):
    """Azure OpenAI API settings."""

    api_key: Optional[str] = Field(None, description="Azure OpenAI API key")
    endpoint: Optional[str] = Field(None, description="Azure OpenAI endpoint")
    deployment_id: str = Field("gpt-4o", description="Azure OpenAI deployment ID")
    api_version: str = Field("2024-05-01", description="Azure OpenAI API version")


class ServiceSettings(BaseModel):
    """Service configuration settings."""

    host: str = Field("0.0.0.0", description="Service host")
    port: int = Field(8000, description="Service port")
    log_level: str = Field("INFO", description="Logging level")
    environment: str = Field("development", description="Deployment environment")
    enable_telemetry: bool = Field(True, description="Enable OpenTelemetry")
    worker_concurrency: int = Field(4, description="Celery worker concurrency")


class IngestionSettings(BaseModel):
    """Ingestion pipeline settings."""

    chunk_size: int = Field(1024, description="Text chunk size for processing")
    chunk_overlap: int = Field(200, description="Overlap between text chunks")
    embedding_model: str = Field("text-embedding-3-large", description="Model for embeddings")
    embedding_dimensions: int = Field(3072, description="Dimensions in embedding vectors")
    retry_attempts: int = Field(3, description="Number of retry attempts")
    retry_backoff: float = Field(2.0, description="Backoff multiplier between retries")


class PluginSettings(BaseModel):
    """Plugin settings."""

    enabled: List[str] = Field(
        ["blarify", "filesystem", "summarizer", "docgrapher"],
        description="List of enabled plugins",
    )
    plugin_directory: str = Field("plugins", description="Directory for plugin discovery")


class TelemetrySettings(BaseModel):
    """Telemetry settings."""

    metrics_port: int = Field(9090, description="Port for Prometheus metrics")
    metrics_endpoint: str = Field("/metrics", description="Endpoint for Prometheus metrics")
    trace_sample_rate: float = Field(1.0, description="OpenTelemetry trace sample rate")
    log_format: str = Field("json", description="Log format")

    @field_validator("log_format")
    def validate_log_format(cls, v: str) -> str:
        """Validate that log format is either 'json' or 'text'."""
        if v not in ["json", "text"]:
            raise ValueError("log_format must be either 'json' or 'text'")
        return v


class AzureSettings(BaseModel):
    """Azure settings."""

    keyvault_name: Optional[str] = Field(None, description="Azure KeyVault name")
    client_id: Optional[str] = Field(None, description="Azure client ID")
    client_secret: Optional[str] = Field(None, description="Azure client secret")
    tenant_id: Optional[str] = Field(None, description="Azure tenant ID")


class Settings(BaseSettings):
    """Main settings class with layered configuration."""

    project_name: str = Field("code-story", description="Project name")
    version: str = Field("0.1.0", description="Project version")
    description: str = Field(
        "A system to convert codebases into richly-linked knowledge graphs with natural-language summaries",
        description="Project description",
    )
    
    # Component settings
    neo4j: Neo4jSettings
    redis: RedisSettings
    openai: OpenAISettings
    azure_openai: AzureOpenAISettings
    service: ServiceSettings
    ingestion: IngestionSettings
    plugins: PluginSettings
    telemetry: TelemetrySettings
    azure: AzureSettings

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        """Initialize settings with layered configuration."""
        # Load settings from .codestory.toml if it exists
        toml_settings = {}
        if os.path.exists(".codestory.toml"):
            with open(".codestory.toml", "rb") as f:
                toml_data = tomli.load(f)
                toml_settings = flatten_dict(toml_data)
        
        # Convert toml settings to environment variables format
        env_dict = {f"{k.upper()}": str(v) for k, v in toml_settings.items()}
        
        # Environment variables take precedence over TOML
        env_dict.update({k: v for k, v in os.environ.items() if k.startswith(("CODESTORY_", "NEO4J_", "REDIS_", "OPENAI_", "AZURE_", "SERVICE_"))})
        
        # Pass the combined settings to pydantic
        super().__init__(**kwargs, **env_dict)


def flatten_dict(d: Dict, parent_key: str = "", sep: str = "__") -> Dict:
    """Flatten nested dictionary with separator in keys."""
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
    """Return cached settings instance."""
    return Settings()