"""Configuration for the MCP Adapter.

This module provides configuration management for the MCP Adapter.
"""

from functools import lru_cache
from typing import Optional

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
    azure_tenant_id: Optional[str] = Field(
        None, description="Microsoft Entra ID tenant ID"
    )
    azure_client_id: Optional[str] = Field(
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
    api_audience: Optional[str] = Field(
        None, description="Audience claim for JWT tokens"
    )
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
    def set_audience(cls, v: Optional[str], info) -> str:
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
        if client_id:
            return client_id

        # Fall back to default audience
        return "api://code-story"


@lru_cache()
def get_mcp_settings() -> MCPSettings:
    """Get MCP settings singleton.

    Returns:
        MCP settings instance
    """
    return MCPSettings()
