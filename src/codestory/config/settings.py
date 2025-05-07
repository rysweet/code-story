from functools import lru_cache
from typing import Any, Literal

from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr


class Neo4jSettings(BaseSettings):
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: SecretStr = SecretStr("password")
    connection_timeout: int = 30
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60

class OpenAISettings(BaseSettings):
    endpoint: str = "https://api.openai.com/v1"
    api_key: SecretStr
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o"
    reasoning_model: str = "gpt-4o"
    max_retries: int = 3
    retry_backoff_factor: float = 2.0

class IngestionSettings(BaseSettings):
    config_path: str = "pipeline_config.yml"
    steps: dict[str, dict[str, Any]] = Field(default_factory=dict)
    max_retries: int = 3
    concurrency: int = 5

class RedisSettings(BaseSettings):
    uri: str = "redis://localhost:6379/0"

class InterfaceSettings(BaseSettings):
    pass  # Extend as needed

class ServiceSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

class Settings(BaseSettings):
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
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            return (
                env_settings,
                init_settings,
                file_secret_settings,
                cls._toml_config,
                cls._keyvault_settings,
            )

        @classmethod
        def _toml_config(cls, settings):
            # TODO: Implement TOML loading
            return {}

        @classmethod
        def _keyvault_settings(cls, settings):
            # TODO: Implement KeyVault loading
            return {}

@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of the Settings."""
    return Settings()
