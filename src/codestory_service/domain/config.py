"""Domain models for configuration management."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ConfigValueType(str, Enum):
    """Type of configuration value."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    SECRET = "secret"
    LIST = "list"
    DICT = "dict"


class ConfigSource(str, Enum):
    """Source of a configuration value."""

    DEFAULT = "default"
    ENV = "env"
    ENV_FILE = "env_file"
    CONFIG_FILE = "config_file"
    KEYVAULT = "keyvault"
    OVERRIDE = "override"


class ConfigSection(str, Enum):
    """Configuration section names."""

    GENERAL = "general"
    NEO4J = "neo4j"
    OPENAI = "openai"
    AZURE = "azure"
    SERVICE = "service"
    INGESTION = "ingestion"
    METRICS = "metrics"
    SECURITY = "security"
    LOGGING = "logging"


class ConfigPermission(str, Enum):
    """Permission level for a configuration key."""

    READ_ONLY = "read_only"  # Cannot be changed through API
    READ_WRITE = "read_write"  # Can be changed but not sensitive
    RESTRICTED = "restricted"  # Requires elevated permissions
    SENSITIVE = "sensitive"  # Contains secrets, should be masked in output


class ConfigMetadata(BaseModel):
    """Metadata for a configuration value."""

    section: ConfigSection = Field(..., description="Configuration section")
    key: str = Field(..., description="Configuration key name")
    type: ConfigValueType = Field(..., description="Type of configuration value")
    description: str = Field(..., description="Description of the configuration key")
    default_value: Optional[Any] = Field(default=None, description="Default value")
    source: ConfigSource = Field(..., description="Source of the current value")
    permission: ConfigPermission = Field(
        ..., description="Permission level for the key"
    )
    env_var: Optional[str] = Field(
        default=None, description="Name of the environment variable"
    )
    required: bool = Field(default=False, description="Whether the value is required")
    json_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON Schema for validation"
    )


class ConfigItem(BaseModel):
    """Single configuration item with value and metadata."""

    value: Any = Field(..., description="Configuration value")
    metadata: ConfigMetadata = Field(..., description="Configuration metadata")

    @property
    def is_sensitive(self) -> bool:
        """Check if the configuration item is sensitive."""
        return (
            self.metadata.type == ConfigValueType.SECRET
            or self.metadata.permission == ConfigPermission.SENSITIVE
        )

    def redact_if_sensitive(self) -> "ConfigItem":
        """Return a new ConfigItem with the value redacted if sensitive."""
        if not self.is_sensitive:
            return self

        return ConfigItem(value="***REDACTED***", metadata=self.metadata)


class ConfigGroup(BaseModel):
    """Group of configuration items in a section."""

    section: ConfigSection = Field(..., description="Configuration section")
    items: Dict[str, ConfigItem] = Field(
        ..., description="Configuration items in this section"
    )


class ConfigDump(BaseModel):
    """Full configuration dump with all values and metadata."""

    groups: Dict[ConfigSection, ConfigGroup] = Field(
        ..., description="Configuration groups by section"
    )
    version: str = Field(..., description="Configuration schema version")
    last_updated: str = Field(..., description="Last update timestamp ISO format")

    def redact_sensitive(self) -> "ConfigDump":
        """Return a new ConfigDump with sensitive values redacted."""
        redacted_groups = {}

        for section, group in self.groups.items():
            redacted_items = {
                key: item.redact_if_sensitive() for key, item in group.items.items()
            }

            redacted_groups[section] = ConfigGroup(
                section=section, items=redacted_items
            )

        return ConfigDump(
            groups=redacted_groups, version=self.version, last_updated=self.last_updated
        )


class ConfigPatchItem(BaseModel):
    """Single configuration item patch."""

    key: str = Field(..., description="Full key path (section.key)")
    value: Any = Field(..., description="New configuration value")


class ConfigPatch(BaseModel):
    """Patch with configuration updates."""

    items: List[ConfigPatchItem] = Field(
        ..., description="Configuration items to update"
    )
    comment: Optional[str] = Field(
        default=None, description="Comment describing the changes"
    )

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[ConfigPatchItem]) -> List[ConfigPatchItem]:
        """Validate that there are items to update."""
        if not v:
            raise ValueError("Config patch must contain at least one item")
        return v


class ConfigSchemaProperty(BaseModel):
    """JSON Schema property for a configuration key."""

    type: str = Field(..., description="JSON Schema type")
    title: str = Field(..., description="Display title")
    description: str = Field(..., description="Property description")
    default: Optional[Any] = Field(default=None, description="Default value")
    enum: Optional[List[Any]] = Field(
        default=None, description="Enum values if applicable"
    )
    format: Optional[str] = Field(
        default=None, description="Format hint (e.g., password)"
    )
    minimum: Optional[float] = Field(
        default=None, description="Minimum value for numbers"
    )
    maximum: Optional[float] = Field(
        default=None, description="Maximum value for numbers"
    )
    minLength: Optional[int] = Field(
        default=None, description="Minimum length for strings"
    )
    maxLength: Optional[int] = Field(
        default=None, description="Maximum length for strings"
    )
    pattern: Optional[str] = Field(
        default=None, description="Regex pattern for strings"
    )
    readOnly: Optional[bool] = Field(
        default=None, description="If true, value is read-only"
    )
    writeOnly: Optional[bool] = Field(
        default=None, description="If true, value is write-only"
    )


class ConfigSchemaSection(BaseModel):
    """JSON Schema for a configuration section."""

    type: str = Field(default="object", description="Always object for sections")
    title: str = Field(..., description="Display title for the section")
    description: str = Field(..., description="Section description")
    properties: Dict[str, ConfigSchemaProperty] = Field(
        ..., description="Properties in this section"
    )
    required: List[str] = Field(
        default_factory=list, description="Required properties in this section"
    )


class ConfigSchema(BaseModel):
    """Full JSON Schema for configuration, used by GUI form generation."""

    json_schema: Dict[str, Any] = Field(..., description="JSON Schema")
    ui_schema: Dict[str, Any] = Field(
        default_factory=dict, description="UI Schema with layout hints"
    )

    @classmethod
    def create_from_config(cls, config: ConfigDump) -> "ConfigSchema":
        """Create a JSON Schema from the configuration."""
        properties = {}
        required = []
        ui_schema = {"ui:order": []}

        for section_name, group in config.groups.items():
            section_properties = {}
            section_required = []
            section_ui = {"ui:order": []}

            for key, item in group.items.items():
                meta = item.metadata

                # Create property schema
                prop = ConfigSchemaProperty(
                    type=meta.type.value,
                    title=key,
                    description=meta.description,
                    default=meta.default_value,
                    readOnly=meta.permission == ConfigPermission.READ_ONLY,
                    writeOnly=meta.permission == ConfigPermission.SENSITIVE,
                )

                # Special handling for type-specific properties
                if meta.type == ConfigValueType.STRING:
                    if meta.json_schema and "pattern" in meta.json_schema:
                        prop.pattern = meta.json_schema["pattern"]
                    if meta.json_schema and "maxLength" in meta.json_schema:
                        prop.maxLength = meta.json_schema["maxLength"]

                # Handle secrets as password fields
                if meta.type == ConfigValueType.SECRET:
                    section_ui[key] = {"ui:widget": "password"}

                section_properties[key] = prop
                section_ui["ui:order"].append(key)

                if meta.required:
                    section_required.append(key)

            # Create section schema
            section_schema = ConfigSchemaSection(
                title=section_name.value.capitalize(),
                description=f"Configuration for {section_name.value}",
                properties=section_properties,
                required=section_required,
            )

            properties[section_name.value] = section_schema
            ui_schema["ui:order"].append(section_name.value)
            ui_schema[section_name.value] = section_ui

        json_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Code Story Configuration",
            "description": "Configuration settings for Code Story service",
            "properties": properties,
            "required": required,
        }

        return cls(json_schema=json_schema, ui_schema=ui_schema)


class ConfigValidationError(BaseModel):
    """Error from configuration validation."""

    path: str = Field(..., description="JSON path to the invalid value")
    message: str = Field(..., description="Error message")
    value: Optional[Any] = Field(default=None, description="Invalid value")


class ConfigValidationResult(BaseModel):
    """Result of configuration validation."""

    valid: bool = Field(..., description="Whether the configuration is valid")
    errors: List[ConfigValidationError] = Field(
        default_factory=list, description="Validation errors if any"
    )
