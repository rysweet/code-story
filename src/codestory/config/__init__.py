"""Configuration module for Code Story.

This module provides a centralized configuration system with the following features:
- Loading configuration from multiple sources with precedence rules
- Strongly-typed configuration interface via Pydantic models
- Integration with Azure KeyVault for secure storage of sensitive values
- Configuration persistence and runtime updates
- Configuration export to various formats

Usage:
    from codestory.config import get_settings

    settings = get_settings()
    neo4j_uri = settings.neo4j.uri

    # Update a setting
    from codestory.config import update_config
    update_config("neo4j.uri", "bolt://neo4j:7687", persist_to="env")
"""

from .exceptions import (
    ConfigurationError,
    KeyVaultError,
    PermissionError,
    SettingNotFoundError,
    SourceError,
    ValidationError,
)
from .export import (
    create_env_template,
    export_to_json,
    export_to_toml,
    settings_to_dict,
)
from .settings import (
    AzureOpenAISettings,
    AzureSettings,
    IngestionSettings,
    InterfaceSettings,
    Neo4jSettings,
    OpenAISettings,
    PluginSettings,
    RedisSettings,
    ServiceSettings,
    Settings,
    TelemetrySettings,
    get_project_root,
    get_settings,
    refresh_settings,
)
from .writer import (
    get_config_value,
    update_config,
    update_env,
    update_toml,
)

__all__ = [
    "AzureOpenAISettings",
    "AzureSettings",
    # Exceptions
    "ConfigurationError",
    "IngestionSettings",
    "InterfaceSettings",
    "KeyVaultError",
    "Neo4jSettings",
    "OpenAISettings",
    "PermissionError",
    "PluginSettings",
    "RedisSettings",
    "ServiceSettings",
    "SettingNotFoundError",
    # Core settings classes
    "Settings",
    "SourceError",
    "TelemetrySettings",
    "ValidationError",
    "create_env_template",
    "export_to_json",
    "export_to_toml",
    "get_config_value",
    "get_project_root",
    # Settings access
    "get_settings",
    "refresh_settings",
    # Configuration export
    "settings_to_dict",
    # Configuration writing
    "update_config",
    "update_env",
    "update_toml",
]
