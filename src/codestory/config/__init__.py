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
    ValidationError,
    SourceError,
    KeyVaultError,
    SettingNotFoundError,
    PermissionError,
)
from .export import (
    settings_to_dict,
    export_to_json,
    export_to_toml,
    create_env_template,
)
from .settings import (
    Settings,
    Neo4jSettings,
    RedisSettings,
    OpenAISettings,
    AzureOpenAISettings,
    ServiceSettings,
    IngestionSettings,
    PluginSettings,
    TelemetrySettings,
    InterfaceSettings,
    AzureSettings,
    get_settings,
    refresh_settings,
    get_project_root,
)
from .writer import (
    update_config,
    update_env,
    update_toml,
    get_config_value,
)

__all__ = [
    # Core settings classes
    "Settings",
    "Neo4jSettings",
    "RedisSettings",
    "OpenAISettings", 
    "AzureOpenAISettings",
    "ServiceSettings",
    "IngestionSettings",
    "PluginSettings",
    "TelemetrySettings",
    "InterfaceSettings",
    "AzureSettings",
    
    # Settings access
    "get_settings",
    "refresh_settings",
    "get_project_root",
    
    # Configuration writing
    "update_config",
    "update_env",
    "update_toml",
    "get_config_value",
    
    # Configuration export
    "settings_to_dict",
    "export_to_json",
    "export_to_toml",
    "create_env_template",
    
    # Exceptions
    "ConfigurationError",
    "ValidationError",
    "SourceError",
    "KeyVaultError",
    "SettingNotFoundError",
    "PermissionError",
]