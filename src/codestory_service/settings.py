"""Settings module for the Code Story Service.

This module provides a specialized settings class for the service, building
on the core settings infrastructure.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from codestory.config.settings import get_settings as get_core_settings

# Set up logging
logger = logging.getLogger(__name__)


class ServiceSettings(BaseSettings):
    """Service-specific settings that extend core settings.

    This class provides FastAPI-specific configuration and
    additional settings needed by the service but not
    by other components.
    """

    # Basic Service Info
    title: str = Field("Code Story API", description="API title for OpenAPI docs")
    summary: str = Field(
        "API for Code Story knowledge graph service",
        description="API summary for OpenAPI docs",
    )
    version: str = Field("0.1.0", description="API version")

    # FastAPI Settings
    api_prefix: str = Field("/v1", description="API version prefix")
    docs_url: str = Field("/docs", description="OpenAPI docs URL")
    openapi_url: str = Field("/openapi.json", description="OpenAPI schema URL")
    redoc_url: str = Field("/redoc", description="ReDoc UI URL")

    # CORS Settings
    cors_origins: List[str] = Field(
        ["*"],
        description="List of allowed origins for CORS (use ['*'] for development)",
    )
    cors_allow_credentials: bool = Field(
        True, description="Allow credentials in CORS requests"
    )
    cors_allow_methods: List[str] = Field(
        ["*"], description="HTTP methods to allow in CORS requests"
    )
    cors_allow_headers: List[str] = Field(
        ["*"], description="HTTP headers to allow in CORS requests"
    )

    # Authentication Settings
    auth_enabled: bool = Field(
        False, description="Enable authentication (disabled for local development)"
    )
    jwt_secret: Optional[SecretStr] = Field(
        None, description="Secret key for JWT tokens (only used in local dev mode)"
    )
    jwt_algorithm: str = Field("HS256", description="Algorithm for JWT tokens")
    jwt_expiration: int = Field(3600, description="JWT token expiration in seconds")

    # WebSocket Settings
    websocket_heartbeat: int = Field(
        30, description="WebSocket heartbeat interval in seconds"
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_requests: int = Field(
        100, description="Number of requests allowed per time window"
    )
    rate_limit_window: int = Field(
        60, description="Time window for rate limiting in seconds"
    )

    # Prometheus metrics
    metrics_enabled: bool = Field(True, description="Enable Prometheus metrics")
    metrics_route: str = Field("/metrics", description="Route for Prometheus metrics")

    # Development mode
    dev_mode: bool = Field(
        True, description="Enable development mode with additional debugging features"
    )

    # Request payload limits
    max_request_size: int = Field(
        10 * 1024 * 1024,  # 10 MB
        description="Maximum size of request payloads in bytes",
    )

    # Response timeouts
    response_timeout: int = Field(
        60, description="Maximum time to wait for responses in seconds"
    )

    # Model config
    model_config = SettingsConfigDict(
        env_prefix="CODESTORY_SERVICE_",
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # We no longer need a custom parser since we use JSON arrays in environment variables

    @field_validator("cors_origins")
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        """Validate CORS origins.

        In production, we want to avoid using '*' for security reasons.
        This validator warns if a wildcard is used in non-development environments.

        Args:
            v: List of CORS origins

        Returns:
            The validated CORS origins
        """
        core_settings = get_core_settings()
        if "*" in v and core_settings.environment != "development":
            logger.warning(
                "Using '*' for CORS origins in non-development environment. "
                "This is a security risk!"
            )
        return v


def get_service_settings() -> ServiceSettings:
    """Get service-specific settings.

    Returns:
        ServiceSettings instance with service-specific configuration
    """
    return ServiceSettings()
