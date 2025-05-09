"""Configuration service for Code Story Service.

This module provides application-level services for managing configuration,
including reading, writing, and validating configuration settings.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from fastapi import HTTPException, status
import redis.asyncio as redis

from codestory.config.settings import get_settings as get_core_settings
from codestory.config.export import export_to_json, export_to_toml, create_env_template
from codestory.config.writer import update_config, update_env, update_toml, get_config_value

# Wrapper class to maintain compatibility
class ConfigWriter:
    """Wrapper for configuration writing functions."""

    def update_config(self, setting_path: str, value: Any, persist_to: Optional[str] = None) -> None:
        """Update a configuration setting."""
        update_config(setting_path, value, persist_to)

    def update_env(self, key: str, value: str, env_file: Optional[str] = None) -> None:
        """Update a value in the .env file."""
        update_env(key, value, env_file)

    def update_toml(self, section: str, key: str, value: Any, toml_file: Optional[str] = None) -> None:
        """Update a value in the .codestory.toml file."""
        update_toml(section, key, value, toml_file)

from ..domain.config import (
    ConfigDump,
    ConfigGroup,
    ConfigItem,
    ConfigMetadata,
    ConfigPatch,
    ConfigPermission,
    ConfigSchema,
    ConfigSection,
    ConfigSource,
    ConfigValidationError,
    ConfigValidationResult,
    ConfigValueType,
)
from ..settings import get_service_settings

# Set up logging
logger = logging.getLogger(__name__)


class ConfigService:
    """Application service for configuration management.

    This service provides methods for reading and writing configuration
    settings, as well as validating configuration changes.
    """

    def __init__(self) -> None:
        """Initialize the configuration service."""
        self.core_settings = get_core_settings()
        self.service_settings = get_service_settings()

        # Initialize Redis for config change notifications
        self.redis = None
        self.notification_channel = "codestory:config:updated"

        # Config writer for persisting changes
        self.writer = ConfigWriter()

        # Track settings that can be hot-reloaded vs require restart
        self.hot_reloadable = {
            "openai.timeout",
            "openai.max_retries",
            "service.rate_limit_enabled",
            "service.rate_limit_requests",
            "service.rate_limit_window",
            "neo4j.timeout",
            "neo4j.max_retries",
            "neo4j.connection_pool_size",
            "logging.level",
        }

        # Initialize Redis connection later to avoid blocking initialization
        self._init_redis_task = None

    async def _init_redis(self) -> None:
        """Initialize Redis connection asynchronously."""
        try:
            # Get Redis connection details from settings
            # In a real implementation, these would be retrieved from settings
            redis_host = "localhost"
            redis_port = 6379
            redis_db = 0

            self.redis = redis.Redis(
                host=redis_host, port=redis_port, db=redis_db, decode_responses=True
            )

            # Ping Redis to verify connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully for config notifications")
        except Exception as e:
            logger.error(
                f"Failed to connect to Redis for config notifications: {str(e)}"
            )
            self.redis = None

    async def notify_config_updated(self, changes: Set[str]) -> None:
        """Notify subscribers that configuration has been updated.

        Args:
            changes: Set of configuration keys that were changed
        """
        if not self.redis:
            # Initialize Redis if not already done
            if not self._init_redis_task:
                self._init_redis_task = self._init_redis()
                await self._init_redis_task
            else:
                await self._init_redis_task

        if not self.redis:
            logger.warning("Redis not available for config notifications")
            return

        try:
            # Prepare notification payload
            notification = {
                "timestamp": int(time.time()),
                "changes": list(changes),
                "requires_restart": any(
                    key not in self.hot_reloadable for key in changes
                ),
            }

            # Publish to Redis
            await self.redis.publish(
                self.notification_channel, json.dumps(notification)
            )

            logger.info(
                f"Published config update notification for {len(changes)} changes"
            )
        except Exception as e:
            logger.error(f"Failed to publish config update notification: {str(e)}")

    def get_config_dump(self, include_sensitive: bool = False) -> ConfigDump:
        """Get a complete dump of the configuration.

        Args:
            include_sensitive: Whether to include sensitive values

        Returns:
            ConfigDump with all configuration values and metadata
        """
        # Export settings to a dictionary structure
        settings_export = self.core_settings.model_dump(by_alias=False, exclude_none=True)
        service_export = self.service_settings.model_dump(by_alias=False, exclude_none=True)

        # Combine core and service settings
        settings_export.update(service_export)

        # Build configuration groups
        groups: Dict[ConfigSection, ConfigGroup] = {}

        # Process settings by section
        for full_key, value in settings_export.items():
            # Skip internal or private keys
            if full_key.startswith("_"):
                continue

            # Split the key into section and name
            parts = full_key.split(".", 1)
            if len(parts) == 1:
                section_name = ConfigSection.GENERAL
                key_name = parts[0]
            else:
                # Try to map the section name to an enum value
                section_name_str = parts[0].upper()
                try:
                    section_name = ConfigSection[section_name_str]
                except KeyError:
                    # If not found, use GENERAL
                    section_name = ConfigSection.GENERAL
                    key_name = full_key
                else:
                    key_name = parts[1]

            # Determine value type
            if isinstance(value, str):
                value_type = ConfigValueType.STRING
            elif isinstance(value, int):
                value_type = ConfigValueType.INTEGER
            elif isinstance(value, float):
                value_type = ConfigValueType.FLOAT
            elif isinstance(value, bool):
                value_type = ConfigValueType.BOOLEAN
            elif isinstance(value, list):
                value_type = ConfigValueType.LIST
            elif isinstance(value, dict):
                value_type = ConfigValueType.DICT
            else:
                value_type = ConfigValueType.STRING

            # Determine if the value is sensitive
            is_sensitive = (
                "password" in key_name.lower()
                or "secret" in key_name.lower()
                or "key" in key_name.lower()
                or "token" in key_name.lower()
            )

            # Create metadata
            metadata = ConfigMetadata(
                section=section_name,
                key=key_name,
                type=value_type,
                description=f"Configuration value for {full_key}",
                source=ConfigSource.CONFIG_FILE,  # Default source
                permission=(
                    ConfigPermission.SENSITIVE
                    if is_sensitive
                    else ConfigPermission.READ_WRITE
                ),
                required=False,  # Default
            )

            # Create config item
            config_item = ConfigItem(value=value, metadata=metadata)

            # Redact sensitive values if requested
            if not include_sensitive and config_item.is_sensitive:
                config_item = config_item.redact_if_sensitive()

            # Add to the appropriate group
            if section_name not in groups:
                groups[section_name] = ConfigGroup(section=section_name, items={})

            groups[section_name].items[key_name] = config_item

        # Create the config dump
        config_dump = ConfigDump(
            groups=groups,
            version="1.0.0",
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        return config_dump

    def get_config_schema(self) -> ConfigSchema:
        """Get the JSON Schema for the configuration.

        Returns:
            ConfigSchema with JSON Schema for the configuration
        """
        # Get the configuration dump
        config_dump = self.get_config_dump(include_sensitive=False)

        # Create schema from the config dump
        return ConfigSchema.create_from_config(config_dump)

    async def update_config(self, patch: ConfigPatch) -> ConfigDump:
        """Update configuration settings.

        Args:
            patch: Configuration changes to apply

        Returns:
            ConfigDump with the updated configuration

        Raises:
            HTTPException: If the configuration update fails
        """
        # Validate the patch
        validation = self._validate_config_patch(patch)
        if not validation.valid:
            error_details = [f"{err.path}: {err.message}" for err in validation.errors]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration: {', '.join(error_details)}",
            )

        try:
            # Track which settings were changed
            changed_keys = set()

            # Apply changes
            for item in patch.items:
                # Parse the full key into section and key
                parts = item.key.split(".", 1)
                if len(parts) == 1:
                    section = "general"
                    key = parts[0]
                else:
                    section = parts[0]
                    key = parts[1]

                # Update the configuration
                if section != "service":
                    # Core settings
                    self.writer.update_setting(
                        section, key, item.value, comment=patch.comment
                    )
                else:
                    # Service settings (would use a different writer in reality)
                    self.writer.update_setting(
                        "service", key, item.value, comment=patch.comment
                    )

                changed_keys.add(item.key)

            # Notify subscribers about the changes
            await self.notify_config_updated(changed_keys)

            # Return the updated configuration
            return self.get_config_dump()
        except Exception as e:
            logger.error(f"Failed to update configuration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update configuration: {str(e)}",
            )

    def _validate_config_patch(self, patch: ConfigPatch) -> ConfigValidationResult:
        """Validate a configuration patch.

        Args:
            patch: Configuration changes to validate

        Returns:
            ConfigValidationResult with validation results
        """
        errors = []

        for item in patch.items:
            # Check if the key exists
            parts = item.key.split(".", 1)
            if len(parts) == 1:
                section = "general"
                key = parts[0]
            else:
                section = parts[0]
                key = parts[1]

            # Check if this is a core or service setting
            found = False
            try:
                # Try to access the setting in the core settings
                if hasattr(self.core_settings, section):
                    section_obj = getattr(self.core_settings, section)
                    if hasattr(section_obj, key):
                        found = True

                # If not found, try the service settings
                if not found and section == "service":
                    setting_key = key
                    if hasattr(self.service_settings, setting_key):
                        found = True
            except Exception:
                pass

            if not found:
                errors.append(
                    ConfigValidationError(
                        path=item.key,
                        message=f"Setting {item.key} does not exist",
                        value=item.value,
                    )
                )
                continue

            # Validate type
            if section != "service":
                # Get the current value to determine the expected type
                try:
                    section_obj = getattr(self.core_settings, section)
                    current_value = getattr(section_obj, key)

                    # Check type compatibility
                    if isinstance(current_value, str) and not isinstance(
                        item.value, str
                    ):
                        errors.append(
                            ConfigValidationError(
                                path=item.key,
                                message=f"Expected string for {item.key}",
                                value=item.value,
                            )
                        )
                    elif isinstance(current_value, int) and not isinstance(
                        item.value, int
                    ):
                        errors.append(
                            ConfigValidationError(
                                path=item.key,
                                message=f"Expected integer for {item.key}",
                                value=item.value,
                            )
                        )
                    elif isinstance(current_value, float) and not (
                        isinstance(item.value, float) or isinstance(item.value, int)
                    ):
                        errors.append(
                            ConfigValidationError(
                                path=item.key,
                                message=f"Expected number for {item.key}",
                                value=item.value,
                            )
                        )
                    elif isinstance(current_value, bool) and not isinstance(
                        item.value, bool
                    ):
                        errors.append(
                            ConfigValidationError(
                                path=item.key,
                                message=f"Expected boolean for {item.key}",
                                value=item.value,
                            )
                        )
                    elif isinstance(current_value, list) and not isinstance(
                        item.value, list
                    ):
                        errors.append(
                            ConfigValidationError(
                                path=item.key,
                                message=f"Expected list for {item.key}",
                                value=item.value,
                            )
                        )
                    elif isinstance(current_value, dict) and not isinstance(
                        item.value, dict
                    ):
                        errors.append(
                            ConfigValidationError(
                                path=item.key,
                                message=f"Expected dictionary for {item.key}",
                                value=item.value,
                            )
                        )
                except Exception as e:
                    logger.warning(f"Error validating {item.key}: {str(e)}")

        return ConfigValidationResult(valid=len(errors) == 0, errors=errors)


def get_config_service() -> ConfigService:
    """Factory function to create a configuration service.

    This is used as a FastAPI dependency.

    Returns:
        ConfigService instance
    """
    return ConfigService()
