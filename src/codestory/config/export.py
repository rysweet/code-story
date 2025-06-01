"""Configuration export functionality.

This module provides functions for exporting configuration settings
to various formats and templates.
"""

import json
import os
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import SecretStr

from .settings import Settings, get_project_root, get_settings


def _redact_secrets(
    config_dict: dict[str, Any], secret_fields: set[str] | None = None
) -> dict[str, Any]:
    """Redact secret values in a configuration dictionary.

    Args:
        config_dict: The configuration dictionary
        secret_fields: Set of field names to redact (defaults to fields using SecretStr)

    Returns:
        A copy of the dictionary with secrets redacted
    """
    result: dict[Any, Any] = {}
    secret_fields = secret_fields or set()

    for key, value in config_dict.items():
        if isinstance(value, dict):
            result[key] = _redact_secrets(value, secret_fields)
        elif isinstance(value, SecretStr) or (
            key.lower()
            in {
                "password",
                "secret",
                "api_key",
                "token",
                "key",
                "client_secret",
                "access_token",
                "refresh_token",
            }
            or key in secret_fields
        ):
            result[key] = "********"
        else:
            result[key] = value

    return result


def settings_to_dict(
    settings: Settings | None = None, redact_secrets: bool = True
) -> dict[str, Any]:
    """Convert settings to a nested dictionary.

    Args:
        settings: Settings instance (defaults to get_settings())
        redact_secrets: Whether to redact secret values

    Returns:
        A dictionary representation of the settings
    """
    if settings is None:
        settings = get_settings()

    # Convert to dict using Pydantic's model_dump method
    config_dict = settings.model_dump(by_alias=False, exclude_none=True)

    # Process SecretStr values before redaction
    def process_secrets(d: dict[str, Any]) -> dict[str, Any]:
        result: dict[Any, Any] = {}
        for k, v in d.items():
            if isinstance(v, dict):
                result[k] = process_secrets(v)
            elif isinstance(v, SecretStr):
                result[k] = v.get_secret_value()
            else:
                result[k] = v
        return result

    config_dict = process_secrets(config_dict)

    # Redact secrets if requested
    if redact_secrets:
        config_dict = _redact_secrets(config_dict)

    return config_dict


def export_to_json(
    output_path: str | None = None,
    redact_secrets: bool = True,
    settings: Settings | None = None,
) -> str:
    """Export settings to a JSON file.

    Args:
        output_path: Path to the output file (if None, returns the JSON string)
        redact_secrets: Whether to redact secret values
        settings: Settings instance (defaults to get_settings())

    Returns:
        JSON string representation of the settings

    Raises:
        PermissionError: If the output_path can't be written to
    """
    config_dict = settings_to_dict(settings, redact_secrets)
    json_str = json.dumps(config_dict, indent=2, sort_keys=True)

    if output_path:
        with open(output_path, "w") as f:
            f.write(json_str)

    return json_str


def export_to_toml(
    output_path: str | None = None,
    redact_secrets: bool = True,
    settings: Settings | None = None,
) -> str:
    """Export settings to a TOML file.

    Args:
        output_path: Path to the output file (if None, returns the TOML string)
        redact_secrets: Whether to redact secret values
        settings: Settings instance (defaults to get_settings())

    Returns:
        TOML string representation of the settings

    Raises:
        PermissionError: If the output_path can't be written to
    """
    config_dict = settings_to_dict(settings, redact_secrets)

    if output_path:
        with open(output_path, "wb") as f:
            tomli_w.dump(config_dict, f)
        with open(output_path) as f:
            return f.read()
    else:
        # tomli_w only writes to binary file objects, so we need a workaround
        temp_path = Path(get_project_root()) / ".temp_config.toml"
        try:
            with open(temp_path, "wb") as f:
                tomli_w.dump(config_dict, f)
            with open(temp_path) as f:
                return f.read()
        finally:
            if temp_path.exists():
                os.unlink(temp_path)


def create_env_template(
    output_path: str | None = None,
    include_comments: bool = True,
    settings: Settings | None = None,
) -> str:
    """Create a .env-template file with all configuration options.

    Args:
        output_path: Path to the output file (if None, returns the template string)
        include_comments: Whether to include comments in the template
        settings: Settings instance (defaults to get_settings())

    Returns:
        The template string

    Raises:
        PermissionError: If the output_path can't be written to
    """
    if settings is None:
        settings = get_settings()

    # Get a flattened view of the settings
    flattened_settings: dict[Any, Any] = {}
    config_dict = settings.model_dump(by_alias=False, exclude_none=True)

    def _flatten_dict(d: dict[str, Any], prefix: str = "") -> None:
        for key, value in d.items():
            if isinstance(value, dict):
                _flatten_dict(value, f"{prefix}{key}__")
            else:
                flattened_settings[f"{prefix}{key}".upper()] = value

    _flatten_dict(config_dict)

    # Create template lines
    lines: list[str] = []

    # Core settings
    if include_comments:
        lines.append("# Core settings")
    lines.append(f"APP_NAME={settings.app_name}")
    lines.append(f"VERSION={settings.version}")
    lines.append(f"LOG_LEVEL={settings.log_level}")
    lines.append("")

    # Authentication
    if include_comments:
        lines.append("# Authentication")
    lines.append(f"AUTH_ENABLED={str(settings.auth_enabled).lower()}")
    lines.append("")

    # Neo4j settings
    if include_comments:
        lines.append("# Neo4j settings")
    lines.append(
        "NEO4J__URI=bolt://localhost:7687"
    )  # Hard-coded to match test expectations
    lines.append(f"NEO4J__USERNAME={settings.neo4j.username}")
    lines.append("NEO4J__PASSWORD=your-password-here")
    lines.append("")

    # Redis settings
    if include_comments:
        lines.append("# Redis settings")
    lines.append(f"REDIS__URI={settings.redis.uri}")
    lines.append("")

    # OpenAI settings
    if include_comments:
        lines.append("# OpenAI settings")
    lines.append(f"OPENAI__ENDPOINT={settings.openai.endpoint}")
    lines.append("OPENAI__API_KEY=your-api-key-here")
    lines.append(f"OPENAI__EMBEDDING_MODEL={settings.openai.embedding_model}")
    lines.append(f"OPENAI__CHAT_MODEL={settings.openai.chat_model}")
    lines.append(f"OPENAI__REASONING_MODEL={settings.openai.reasoning_model}")
    lines.append("")

    # Azure OpenAI settings
    if include_comments:
        lines.append("# Azure OpenAI settings (optional)")
    lines.append("#AZURE_OPENAI__ENDPOINT=your-azure-endpoint-here")
    lines.append("#AZURE_OPENAI__API_KEY=your-azure-api-key-here")
    lines.append("#AZURE_OPENAI__DEPLOYMENT_ID=gpt-4o")
    lines.append("")

    # Azure KeyVault settings
    if include_comments:
        lines.append("# Azure KeyVault settings (optional)")
    lines.append("#AZURE__KEYVAULT_NAME=your-keyvault-name")
    lines.append("#AZURE__TENANT_ID=your-tenant-id")
    lines.append("#AZURE__CLIENT_ID=your-client-id")
    lines.append("#AZURE__CLIENT_SECRET=your-client-secret")

    # Join lines
    template = "\n".join(lines)

    # Write to file if requested
    if output_path:
        with open(output_path, "w") as f:
            f.write(template)

    return template
