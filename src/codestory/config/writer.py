"""Configuration writer module.

This module provides functions for updating configuration values at runtime
and persisting those changes to .env or .codestory.toml files.
"""

import os
from pathlib import Path
from typing import Any

import tomli
import tomli_w
from dotenv import load_dotenv, set_key
from pydantic import SecretStr

from .exceptions import SettingNotFoundError
from .settings import get_project_root, get_settings, refresh_settings


def update_env(key: str, value: str, env_file: str | None = None) -> None:
    """Update a value in the .env file.

    Args:
        key: The environment variable key (will be converted to uppercase)
        value: The value to set
        env_file: Path to the .env file (defaults to project root/.env)

    Raises:
        FileNotFoundError: If the env_file doesn't exist
        PermissionError: If the env_file can't be written to
    """
    if env_file is None:
        env_file = str(get_project_root() / ".env")

    # Create the file if it doesn't exist
    if not os.path.exists(env_file):
        Path(env_file).touch()

    # Set the key in the .env file (dotenv handles creating the file if needed)
    set_key(env_file, key.upper(), str(value), quote_mode="always")

    # Reload environment variables
    load_dotenv(env_file, override=True)


def update_toml(
    section: str,
    key: str,
    value: Any,
    toml_file: str | None = None,
    create_if_missing: bool = True,
) -> None:
    """Update a value in the .codestory.toml file.

    Args:
        section: The TOML section (top-level key)
        key: The key within the section
        value: The value to set
        toml_file: Path to the TOML file (defaults to project root/.codestory.toml)
        create_if_missing: Whether to create the file if it doesn't exist

    Raises:
        FileNotFoundError: If the toml_file doesn't exist and create_if_missing is False
        PermissionError: If the toml_file can't be written to
        ValueError: If the value type isn't supported by TOML
    """
    if toml_file is None:
        toml_file = str(get_project_root() / ".codestory.toml")

    # Load existing TOML if it exists
    config: dict[str, Any] = {}
    if os.path.exists(toml_file):
        with open(toml_file, "rb") as f:
            try:
                config = tomli.load(f)
            except Exception as e:
                raise ValueError(f"Error parsing {toml_file}: {e}") from e
    elif not create_if_missing:
        raise FileNotFoundError(f"TOML file {toml_file} does not exist")

    # Create the section if it doesn't exist
    if section not in config:
        config[section] = {}

    # Handle nested keys with dot notation
    if "." in key:
        parts = key.split(".")
        current = config[section]
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    else:
        # Set the value in the config
        config[section][key] = value

    # Write the updated config back to the file
    with open(toml_file, "wb") as f:
        tomli_w.dump(config, f)


def parse_setting_path(setting_path: str) -> tuple[str, str]:
    """Parse a setting path into section and key parts.

    Args:
        setting_path: A string like 'neo4j.uri' or 'openai.api_key'

    Returns:
        A tuple of (section, key)

    Raises:
        ValueError: If the setting_path is not in the format 'section.key'
    """
    parts = setting_path.split(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Setting path '{setting_path}' should be in format 'section.key'")
    return parts[0], parts[1]


def update_config(
    setting_path: str,
    value: Any,
    persist_to: str | None = None,
) -> None:
    """Update a configuration setting in memory and optionally persist to file.

    Args:
        setting_path: Path to the setting in dot notation (e.g., 'neo4j.uri')
        value: The value to set
        persist_to: Where to persist the change ('env', 'toml', or None for in-memory only)

    Example:
        >>> update_config('neo4j.uri', 'bolt://neo4j:7687', 'env')
        >>> update_config('openai.temperature', 0.7, 'toml')

    Raises:
        ValueError: If the setting_path is invalid or the value type is not compatible
        FileNotFoundError: If the specified file doesn't exist
        PermissionError: If the file can't be written to
    """
    section, key = parse_setting_path(setting_path)

    # Get the current settings
    settings = get_settings()

    # Check if the section exists
    if not hasattr(settings, section):
        raise SettingNotFoundError(setting_path)

    section_obj = getattr(settings, section)

    # Check if the key exists in the section
    if not hasattr(section_obj, key):
        raise SettingNotFoundError(setting_path)

    # Handle SecretStr values
    current_value = getattr(section_obj, key)
    if isinstance(current_value, SecretStr) and not isinstance(value, SecretStr):
        value = SecretStr(str(value))

    # Update the in-memory value
    # Note: This doesn't work with the cached Settings instance
    # We'll need to clear the cache to see the changes
    setattr(section_obj, key, value)

    # Persist to file if requested
    if persist_to == "env":
        env_key = f"{section.upper()}__{key.upper()}"
        value_str = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        update_env(env_key, value_str)
    elif persist_to == "toml":
        value_to_save = value.get_secret_value() if isinstance(value, SecretStr) else value
        update_toml(section, key, value_to_save)

    # Clear the settings cache to force reloading on next access
    refresh_settings()


def get_config_value(setting_path: str) -> Any:
    """Get a configuration value by path.

    Args:
        setting_path: Path to the setting in dot notation (e.g., 'neo4j.uri')

    Returns:
        The value of the setting

    Raises:
        ValueError: If the setting_path is invalid
        SettingNotFoundError: If the setting doesn't exist
    """
    section, key = parse_setting_path(setting_path)

    # Get the current settings
    settings = get_settings()

    # Check if the section exists
    if not hasattr(settings, section):
        raise SettingNotFoundError(setting_path)

    section_obj = getattr(settings, section)

    # Check if the key exists in the section
    if not hasattr(section_obj, key):
        raise SettingNotFoundError(setting_path)

    # Return the value
    value = getattr(section_obj, key)

    # Handle SecretStr values
    if isinstance(value, SecretStr):
        return value.get_secret_value()

    return value
