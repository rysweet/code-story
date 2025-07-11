from typing import Any

"""Configuration for the MCP Adapter.

This module provides configuration management for the MCP Adapter.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    """Configuration settings for the MCP Adapter.

    Attributes:
        port: Port for the MCP server
        host: Host address to bind
        workers: Number of worker processes
        azure_tenant_id: Microsoft Entra ID tenant ID
        azure_client_id: Client ID for the MCP adapter
        auth_enabled: Enable/disable authentication
        code_story_service_url: URL of the Code Story service
        api_token_issuer: Issuer claim for JWT tokens
        api_audience: Audience claim for JWT tokens
        required_scopes: Required scopes for authorization
        cors_origins: Allowed CORS origins
        enable_grpc: Enable gRPC server
        prometheus_metrics_path: Path for Prometheus metrics
        enable_opentelemetry: Enable OpenTelemetry tracing
        openapi_url: URL for OpenAPI documentation
        docs_url: URL for Swagger UI documentation
        redoc_url: URL for ReDoc documentation
        debug: Enable debug mode
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Customizations to match test behavior
        env_nested_delimiter="__",
    )

    # Server configuration
    port: int = Field(8001, description="Port for the MCP server")
    host: str = Field("0.0.0.0", description="Host address to bind")
    workers: int = Field(4, description="Number of worker processes")

    # Authentication
    azure_tenant_id: str | None = Field(
        None, description="Microsoft Entra ID tenant ID"
    )
    azure_client_id: str | None = Field(
        None, description="Client ID for the MCP adapter"
    )
    auth_enabled: bool = Field(False, description="Enable/disable authentication")

    # Service configuration
    code_story_service_url: str = Field(
        "http://localhost:8000", description="URL of the Code Story service"
    )

    # JWT configuration
    api_token_issuer: str = Field(
        "https://sts.windows.net/", description="Issuer claim for JWT tokens"
    )
    api_audience: str | None = Field(None, description="Audience claim for JWT tokens")
    required_scopes: list[str] = Field(
        ["code-story.read", "code-story.query"],
        description="Required scopes for authorization",
    )

    # CORS configuration
    cors_origins: list[str] = Field(["*"], description="Allowed CORS origins")

    # gRPC configuration
    enable_grpc: bool = Field(True, description="Enable gRPC server")

    # Metrics and tracing
    prometheus_metrics_path: str = Field(
        "/metrics", description="Path for Prometheus metrics"
    )
    enable_opentelemetry: bool = Field(
        False, description="Enable OpenTelemetry tracing"
    )

    # Documentation
    openapi_url: str = Field(
        "/openapi.json", description="URL for OpenAPI documentation"
    )
    docs_url: str = Field("/docs", description="URL for Swagger UI documentation")
    redoc_url: str = Field("/redoc", description="URL for ReDoc documentation")

    # Debug mode
    debug: bool = Field(False, description="Enable debug mode")

    @field_validator("api_audience", mode="before")
    @classmethod
    def set_audience(cls, v: str | None, info: Any) -> str:
        """Set default audience based on client ID.

        Args:
            v: Provided audience value
            info: Validation context data

        Returns:
            Audience value
        """
        if v:
            return v

        # Use client ID as audience if not specified
        client_id = info.data.get("azure_client_id")
        if client_id is not None:
            return str(client_id)

        # Fall back to default audience
        return "api://code-story"


@lru_cache
def get_mcp_settings() -> MCPSettings:
    """Get MCP settings singleton.

    Returns:
        MCP settings instance
    """
    return MCPSettings()  # type: ignore[call-arg]  # TODO: Pydantic BaseSettings with defaults
import os
import logging
from codestory.config.settings import get_settings

def get_azure_openai_config() -> dict:
    """
    Assemble Azure OpenAI endpoint, deployment ID, API version, and API key from environment or config.
    Returns a dict with all relevant config and the fully assembled endpoint URI.
    """
    logger = logging.getLogger(__name__)

    # Priority: env vars (double underscore), then single underscore, then config
    env = os.environ

    # Endpoint
    endpoint = (
        env.get("AZURE_OPENAI__ENDPOINT")
        or env.get("AZURE_OPENAI_ENDPOINT")
        or None
    )
    # Deployment ID
    deployment_id = (
        env.get("AZURE_OPENAI__DEPLOYMENT_ID")
        or env.get("AZURE_OPENAI_MODEL_CHAT")
        or env.get("AZURE_OPENAI_DEPLOYMENT_ID")
        or None
    )
    # API version
    api_version = (
        env.get("AZURE_OPENAI__API_VERSION")
        or env.get("AZURE_OPENAI_API_VERSION")
        or None
    )
    # API key
    api_key = (
        env.get("AZURE_OPENAI__API_KEY")
        or env.get("AZURE_OPENAI_KEY")
        or env.get("OPENAI__API_KEY")
        or env.get("OPENAI_API_KEY")
        or None
    )

    # Fallback to config if not set
    settings = get_settings()
    if not endpoint:
        endpoint = getattr(settings.openai, "endpoint", None)
    if not deployment_id:
        deployment_id = getattr(settings.openai, "chat_model", None)
    if not api_version:
        api_version = getattr(settings.openai, "api_version", None)
    if not api_key:
        api_key = getattr(settings.openai, "api_key", None)
        if api_key is not None and hasattr(api_key, "get_secret_value"):
            api_key = api_key.get_secret_value()

    # Validate required fields
    missing = []
    if not endpoint:
        missing.append("endpoint")
    if not deployment_id:
        missing.append("deployment_id")
    if not api_version:
        missing.append("api_version")
    if not api_key:
        missing.append("api_key")
    if missing:
        logger.error(f"Missing Azure OpenAI config values: {missing}")
        raise RuntimeError(f"Missing Azure OpenAI config values: {missing}")

    # Assemble full endpoint URI for chat completions
    # Example: https://ai-adapt-oai-eastus2.openai.azure.com/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview
    if endpoint.endswith("/"):
        endpoint = endpoint.rstrip("/")
    full_uri = f"{endpoint}/openai/deployments/{deployment_id}/chat/completions?api-version={api_version}"

    # Log all config values (except api_key)
    logger.debug(f"[Azure OpenAI Config] endpoint={endpoint}")
    logger.debug(f"[Azure OpenAI Config] deployment_id={deployment_id}")
    logger.debug(f"[Azure OpenAI Config] api_version={api_version}")
    logger.debug(f"[Azure OpenAI Config] full_uri={full_uri}")

    return {
        "endpoint": endpoint,
        "deployment_id": deployment_id,
        "api_version": api_version,
        "api_key": api_key,
        "full_uri": full_uri,
    }
