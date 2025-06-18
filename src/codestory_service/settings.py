"""Settings module for the Code Story Service.

This module provides a specialized settings class for the service, building
on the core settings infrastructure.
"""

import logging
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from codestory.config.settings import get_settings, Settings
from pathlib import Path
from pydantic import BaseModel
import os

# Set up logging
logger = logging.getLogger(__name__)


# --- Host-Native Deployment Settings ---

class DeploymentSettings(BaseModel):
    mode: str = Field("host", description="Deployment mode: host, docker, hybrid")
    data_directory: Path = Field(Path.home() / ".codestory")
    log_directory: Path = Field(Path("/var/log/codestory"))
    pid_directory: Path = Field(Path("/var/run/codestory"))

class BlarifySettings(BaseModel):
    docker_image: str = Field("blarapp/blarify:latest")
    container_network: str = Field("host")
    volume_mounts: dict[str, str] = Field(default_factory=dict)
    environment_variables: dict[str, str] = Field(default_factory=dict)

class HostNativeSettings:
    """Host-native settings wrapper for host deployments (not a Pydantic model)."""
    def __init__(self, **kwargs):
        # Compose a Settings instance
        self.settings = Settings(**kwargs)
        # Override Neo4j and Redis URIs to localhost for host-native
        self.settings.neo4j.uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        print(f"[service startup] NEO4J_URI in os.environ: {os.environ.get('NEO4J_URI')}")
        print(f"[service startup] Effective Neo4j URI: {self.settings.neo4j.uri}")
        self.settings.redis.uri = "redis://localhost:6379"
        self.deployment = DeploymentSettings()
        self.blarify = BlarifySettings()

    def __getattr__(self, name):
        # Delegate attribute access to the wrapped Settings instance
        return getattr(self.settings, name)

# --- END Host-Native Deployment Settings ---

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
    cors_origins: list[str] = Field(
        ["*"],
        description="List of allowed origins for CORS (use ['*'] for development)",
    )
    cors_allow_credentials: bool = Field(
        True, description="Allow credentials in CORS requests"
    )
    cors_allow_methods: list[str] = Field(
        ["*"], description="HTTP methods to allow in CORS requests"
    )
    cors_allow_headers: list[str] = Field(
        ["*"], description="HTTP headers to allow in CORS requests"
    )

    # Authentication Settings
    auth_enabled: bool = Field(
        False, description="Enable authentication (disabled for local development)"
    )
    jwt_secret: SecretStr | None = Field(
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
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """Validate CORS origins.

        In production, we want to avoid using '*' for security reasons.
        This validator warns if a wildcard is used in non-development environments.

        Args:
            v: List of CORS origins

        Returns:
            The validated CORS origins
        """
        try:
            # Get core settings to check environment
            core_settings = get_core_settings()

            # Check for wildcard origins in production environment
            if core_settings.environment == "production" and "*" in v:
                logger.warning(
                    "Using wildcard (*) CORS origin in production is a security risk. "
                    "Consider specifying exact origins instead."
                )
        except Exception as e:
            # Log warning but don't fail validation
            logger.debug(f"Error during CORS origins validation: {e}")

        return v


def get_core_settings() -> Any:
    """Get core settings from the main settings module.

    Returns:
        Settings instance from the main config module
    """
    return get_settings()


def get_settings(path: str | None = None) -> Settings | HostNativeSettings:
    """
    Deployment-mode aware settings factory.

    Returns:
        HostNativeSettings if DEPLOYMENT_MODE=host or path endswith .host.toml,
        otherwise standard Settings.
    """
    mode_env = os.getenv("DEPLOYMENT_MODE", "").lower()
    if mode_env == "host":
        return HostNativeSettings(_env_file=path or ".env")
    if path and path.endswith(".host.toml"):
        return HostNativeSettings(_env_file=path)
    return Settings(_env_file=path or ".env")

def get_host_native_settings() -> HostNativeSettings:
    """
    Deprecated: Use get_settings() with DEPLOYMENT_MODE=host or path='.codestory.host.toml'.
    """
    mode_env = os.environ.get("DEPLOYMENT_MODE", "").lower()
    if mode_env == "host":
        return HostNativeSettings()
    # No longer triggers on file presence.
    return Settings()

def get_service_settings() -> ServiceSettings:
    """Get service-specific settings.

    Returns:
        ServiceSettings instance with service-specific configuration
    """
    return ServiceSettings()  # type: ignore[call-arg]  # mypy false positive: Pydantic fields have defaults

__all__ = [
    "DeploymentSettings",
    "BlarifySettings",
    "HostNativeSettings",
    "get_host_native_settings",
    "ServiceSettings",
    "get_service_settings",
]
