

"""Settings and configuration models for Code Story.

This module defines the Pydantic settings models and configuration loading logic.
"""

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Neo4jSettings(BaseSettings):
    """Settings for Neo4j graph database connection."""

    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: SecretStr = SecretStr("password")
    connection_timeout: int = 30
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60



class OpenAISettings(BaseSettings):
    """Settings for OpenAI API integration."""

    endpoint: str = "https://api.openai.com/v1"
    api_key: SecretStr
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o"
    reasoning_model: str = "gpt-4o"
    max_retries: int = 3
    retry_backoff_factor: float = 2.0



class IngestionSettings(BaseSettings):
    """Settings for the ingestion pipeline."""

    config_path: str = "pipeline_config.yml"
    steps: dict[str, dict[str, Any]] = Field(default_factory=dict)
    max_retries: int = 3
    concurrency: int = 5



class RedisSettings(BaseSettings):
    """Settings for Redis connection."""

    uri: str = "redis://localhost:6379/0"



class InterfaceSettings(BaseSettings):
    """Settings for interface configuration (extend as needed)."""

    pass



class ServiceSettings(BaseSettings):
    """Settings for the main service (API server)."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4



class Settings(BaseSettings):
    """Top-level application settings for Code Story."""

    app_name: str = "code-story"
    environment: Literal["development", "testing", "production"] = "development"
    log_level: str = "INFO"
    neo4j: Neo4jSettings = Neo4jSettings()
    redis: RedisSettings = RedisSettings()
    auth_enabled: bool = False
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_keyvault_name: str | None = None
    openai: OpenAISettings = OpenAISettings(api_key=SecretStr(""))
    ingestion: IngestionSettings = IngestionSettings()
    interface: InterfaceSettings = InterfaceSettings()
    service: ServiceSettings = ServiceSettings()

    class Config:
        """Pydantic config for environment and file loading."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False

        @classmethod
        def customise_sources(
            cls,
            init_settings: Any,
            env_settings: Any,
            file_secret_settings: Any
        ) -> tuple[Any, ...]:
            """Customize the order of config sources for Pydantic settings."""
            return (
                env_settings,
                init_settings,
                file_secret_settings,
                cls._toml_config,
                cls._keyvault_settings,
            )

        @classmethod
        def _toml_config(cls, settings: Any) -> dict[str, Any]:
            """Load settings from TOML config file."""
            # TODO: Implement TOML loading
            return {}

        @classmethod
        def _keyvault_settings(cls, settings: Any) -> dict[str, Any]:
            """Load settings from Azure KeyVault."""
            # TODO: Implement KeyVault loading
            return {}

@lru_cache
def get_settings() -> "Settings":
    """Return a cached instance of the Settings."""
    return Settings()
