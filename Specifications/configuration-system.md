# Code Story: Configuration System

This document details the configuration system for the Code Story simplified architecture, explaining the design decisions, implementation details, and usage patterns.

## Overview

The configuration system provides a unified approach to manage settings across all components. It replaces the fragmented configuration approach from the microservices architecture with a centralized, hierarchical system that supports:

1. Default values for all settings
2. Environment variable overrides
3. Configuration file overrides
4. Command-line parameter overrides
5. Validation of configuration values
6. Documentation of available settings

## Design Principles

- **Simplicity**: Easy to understand and use, with minimal dependencies
- **Hierarchical**: Configuration organized into logical sections
- **Strongly Typed**: All configuration values have well-defined types and validation
- **Centralized**: One source of truth for all configuration
- **Default-based**: Sensible defaults for all settings to enable "zero-config" operation
- **Discoverable**: Easy to find and understand available configuration options
- **Environment-aware**: Different values for development, testing, and production
- **Minimal Dependencies**: Built with Python standard library where possible

## Configuration Structure

The configuration is organized hierarchically:

```
config/
  ├── defaults.py        # Default configuration values
  ├── schema.py          # Pydantic models defining configuration structure
  ├── environment.py     # Environment variable mapping and loading
  ├── file_loader.py     # Configuration file loading
  ├── config_manager.py  # Main configuration management class
  └── cli.py             # Command-line argument processing
```

## Configuration Hierarchy

Configuration values are applied in this order (later overrides earlier):

1. Built-in defaults
2. Configuration files 
3. Environment variables
4. Command-line arguments

## Configuration Schema

The configuration schema is defined using Pydantic models:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Union, Literal
import os

class StorageConfig(BaseModel):
    """Storage configuration."""
    type: Literal["sqlite", "neo4j"] = Field(
        default="sqlite",
        description="Storage backend type"
    )
    
    # SQLite settings
    sqlite_path: str = Field(
        default="./data/codestory.db",
        description="Path to SQLite database file"
    )
    
    # Neo4j settings
    neo4j_uri: Optional[str] = Field(
        default=None,
        description="Neo4j connection URI"
    )
    neo4j_user: Optional[str] = Field(
        default=None,
        description="Neo4j username"
    )
    neo4j_password: Optional[str] = Field(
        default=None,
        description="Neo4j password"
    )
    
    @validator('neo4j_uri', 'neo4j_user', 'neo4j_password', always=True)
    def validate_neo4j_config(cls, v, values, **kwargs):
        if values.get('type') == 'neo4j':
            if v is None:
                field_name = kwargs['field'].name
                raise ValueError(f"{field_name} is required when type is 'neo4j'")
        return v

class ProcessingConfig(BaseModel):
    """Processing engine configuration."""
    engine: Literal["direct", "celery"] = Field(
        default="direct",
        description="Processing engine type"
    )
    
    # Celery settings
    celery_broker_url: Optional[str] = Field(
        default=None, 
        description="Celery broker URL"
    )
    celery_result_backend: Optional[str] = Field(
        default=None,
        description="Celery result backend URL"
    )
    
    @validator('celery_broker_url', 'celery_result_backend', always=True)
    def validate_celery_config(cls, v, values, **kwargs):
        if values.get('engine') == 'celery':
            if v is None:
                field_name = kwargs['field'].name
                raise ValueError(f"{field_name} is required when engine is 'celery'")
        return v

class ApiConfig(BaseModel):
    """API service configuration."""
    host: str = Field(
        default="127.0.0.1",
        description="API server host"
    )
    port: int = Field(
        default=8000,
        description="API server port"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    auth_enabled: bool = Field(
        default=False,
        description="Enable authentication"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication"
    )

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file: Optional[str] = Field(
        default=None,
        description="Log file path (if not set, logs to stdout)"
    )

class StepConfig(BaseModel):
    """Configuration for a pipeline step."""
    enabled: bool = Field(
        default=True,
        description="Whether the step is enabled"
    )
    timeout_seconds: int = Field(
        default=3600,
        description="Maximum execution time in seconds"
    )
    # Step-specific settings would be defined in subclasses

class FilesystemStepConfig(StepConfig):
    """Configuration for the filesystem step."""
    exclude_patterns: List[str] = Field(
        default=[".git", "node_modules", "__pycache__", "*.pyc"],
        description="Patterns to exclude from file scan"
    )
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file size in megabytes"
    )

class BlarifyStepConfig(StepConfig):
    """Configuration for the blarify step."""
    language_filter: Optional[List[str]] = Field(
        default=None,
        description="Filter for specific languages (None = all supported)"
    )
    parse_docstrings: bool = Field(
        default=True,
        description="Extract and parse docstrings"
    )

class SummarizerStepConfig(StepConfig):
    """Configuration for the summarizer step."""
    model: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model to use for summarization"
    )
    max_tokens: int = Field(
        default=500,
        description="Maximum tokens for summary generation"
    )
    temperature: float = Field(
        default=0.2,
        description="Temperature for generation (0.0-1.0)"
    )

class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    steps: Dict[str, Union[StepConfig, FilesystemStepConfig, BlarifyStepConfig, SummarizerStepConfig]] = Field(
        default_factory=lambda: {
            "filesystem": FilesystemStepConfig(),
            "blarify": BlarifyStepConfig(),
            "summarizer": SummarizerStepConfig(),
            # Additional steps would be added here
        },
        description="Configuration for each pipeline step"
    )
    default_steps: List[str] = Field(
        default=["filesystem", "blarify", "summarizer"],
        description="Default steps to execute"
    )

class AppConfig(BaseModel):
    """Main application configuration."""
    storage: StorageConfig = Field(
        default_factory=StorageConfig,
        description="Storage configuration"
    )
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Processing configuration"
    )
    api: ApiConfig = Field(
        default_factory=ApiConfig,
        description="API configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    pipeline: PipelineConfig = Field(
        default_factory=PipelineConfig,
        description="Pipeline configuration"
    )
    data_dir: str = Field(
        default="./data",
        description="Directory for storing application data"
    )
    temp_dir: str = Field(
        default="/tmp/codestory",
        description="Directory for temporary files"
    )
```

## Environment Variable Mapping

Environment variables are mapped to configuration options following this pattern:

```
CODESTORY_SECTION_OPTION
```

For example:
- `CODESTORY_STORAGE_TYPE=neo4j` sets the storage type to Neo4j
- `CODESTORY_API_PORT=9000` sets the API port to 9000
- `CODESTORY_PIPELINE_STEPS_SUMMARIZER_MODEL=gpt-4` sets the summarizer model to GPT-4

Nested options use additional underscores:
```
CODESTORY_PIPELINE_STEPS_FILESYSTEM_EXCLUDE_PATTERNS=.git,node_modules
```

Boolean values accept various string formats:
- `"true"`, `"yes"`, `"1"`, `"on"` for True
- `"false"`, `"no"`, `"0"`, `"off"` for False

## Configuration Files

Configuration files can be in YAML, JSON, or TOML format. Example YAML configuration:

```yaml
storage:
  type: neo4j
  neo4j_uri: bolt://localhost:7687
  neo4j_user: neo4j
  neo4j_password: password

processing:
  engine: direct

api:
  host: 0.0.0.0
  port: 8000
  debug: true
  cors_origins:
    - http://localhost:3000
    - https://example.com
  
logging:
  level: DEBUG
  file: logs/codestory.log

pipeline:
  default_steps:
    - filesystem
    - blarify
    - summarizer
  steps:
    filesystem:
      exclude_patterns:
        - .git
        - node_modules
        - __pycache__
        - "*.pyc"
      max_file_size_mb: 5
    blarify:
      language_filter:
        - python
        - javascript
      parse_docstrings: true
    summarizer:
      model: gpt-4
      max_tokens: 1000
      temperature: 0.3
```

Configuration files are searched in the following locations (in order):
1. `./config.yaml` (current directory)
2. `~/.config/codestory/config.yaml` (user config directory)
3. `/etc/codestory/config.yaml` (system config directory)
4. Path specified by `CODESTORY_CONFIG_PATH` environment variable

## Configuration Manager

The configuration manager is responsible for loading and providing access to configuration:

```python
from pathlib import Path
import os
import yaml
import json
import toml
from typing import Any, Dict, List, Optional, Union, Type, TypeVar
from pydantic import BaseModel, ValidationError

from .schema import AppConfig

T = TypeVar('T')

class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path
        self._config = self._load_config()
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in standard locations."""
        if self.config_path:
            path = Path(self.config_path)
            if path.exists():
                return path
        
        # Check environment variable
        env_path = os.environ.get("CODESTORY_CONFIG_PATH")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path
        
        # Check standard locations
        paths = [
            Path("./config.yaml"),
            Path("./config.json"),
            Path("./config.toml"),
            Path.home() / ".config" / "codestory" / "config.yaml",
            Path("/etc/codestory/config.yaml"),
        ]
        
        for path in paths:
            if path.exists():
                return path
        
        return None
    
    def _load_file_config(self, path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        with open(path, "r") as f:
            if path.suffix == ".yaml" or path.suffix == ".yml":
                return yaml.safe_load(f)
            elif path.suffix == ".json":
                return json.load(f)
            elif path.suffix == ".toml":
                return toml.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        prefix = "CODESTORY_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split("_")
                
                # Build nested dictionary
                current = env_config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set value, converting to appropriate type
                current[parts[-1]] = self._parse_env_value(value)
        
        return env_config
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Boolean values
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False
        
        # List values (comma-separated)
        if "," in value:
            return [self._parse_env_value(v.strip()) for v in value.split(",")]
        
        # Numeric values
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            # String value
            return value
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._merge_configs(result[key], value)
            else:
                # Override or add value
                result[key] = value
        
        return result
    
    def _load_config(self) -> AppConfig:
        """Load configuration from all sources."""
        # Start with default config (empty dictionary, defaults from model)
        config_dict = {}
        
        # Load configuration file if found
        config_file = self._find_config_file()
        if config_file:
            file_config = self._load_file_config(config_file)
            config_dict = self._merge_configs(config_dict, file_config)
        
        # Apply environment variable overrides
        env_config = self._load_env_config()
        config_dict = self._merge_configs(config_dict, env_config)
        
        # Create and validate the configuration object
        try:
            return AppConfig(**config_dict)
        except ValidationError as e:
            # Convert validation error to more readable format
            error_messages = []
            for error in e.errors():
                path = ".".join(str(p) for p in error["loc"])
                message = error["msg"]
                error_messages.append(f"{path}: {message}")
            
            raise ValueError(
                f"Configuration validation failed:\n" + 
                "\n".join(error_messages)
            )
    
    def get_config(self) -> AppConfig:
        """Get the complete configuration."""
        return self._config
    
    def get_section(self, section: str) -> Any:
        """Get a specific configuration section."""
        if hasattr(self._config, section):
            return getattr(self._config, section)
        raise ValueError(f"Configuration section not found: {section}")
    
    def get_value(self, path: str, default: Optional[T] = None) -> Union[Any, T]:
        """Get a configuration value by path.
        
        Args:
            path: Dot-separated path to configuration value (e.g., "api.port")
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        parts = path.split(".")
        current = self._config
        
        try:
            for part in parts:
                if hasattr(current, part):
                    current = getattr(current, part)
                else:
                    return default
            return current
        except (AttributeError, KeyError):
            return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self._config.dict()
    
    def generate_env_file(self, path: str) -> None:
        """Generate example .env file with all possible environment variables.
        
        Args:
            path: Path to write .env file
        """
        config_dict = self.to_dict()
        env_vars = []
        
        def process_dict(d, prefix="CODESTORY"):
            for key, value in d.items():
                env_key = f"{prefix}_{key.upper()}"
                
                if isinstance(value, dict):
                    process_dict(value, env_key)
                else:
                    env_vars.append(f"# {key} - {type(value).__name__}")
                    env_vars.append(f"# {env_key}={value}")
                    env_vars.append("")
        
        process_dict(config_dict)
        
        with open(path, "w") as f:
            f.write("\n".join(env_vars))
    
    def generate_documentation(self) -> str:
        """Generate markdown documentation for all configuration options."""
        from pydantic import schema_json_of
        import json
        
        # Get JSON schema
        schema_json = schema_json_of(AppConfig)
        schema = json.loads(schema_json)
        
        lines = ["# Configuration Options", ""]
        
        def process_schema(s, prefix=""):
            if "properties" in s:
                for name, prop in s["properties"].items():
                    full_name = f"{prefix}.{name}" if prefix else name
                    
                    # Add section header
                    if prefix == "" and "properties" in prop:
                        lines.append(f"## {name}")
                        lines.append("")
                    elif "properties" not in prop:
                        # Add property documentation
                        lines.append(f"### {full_name}")
                        lines.append("")
                        
                        if "description" in prop:
                            lines.append(prop["description"])
                            lines.append("")
                        
                        lines.append(f"**Type:** {prop.get('type', 'object')}")
                        
                        if "default" in prop:
                            lines.append(f"**Default:** `{prop['default']}`")
                        
                        if "enum" in prop:
                            lines.append(f"**Allowed values:** {', '.join([f'`{v}`' for v in prop['enum']])}")
                        
                        lines.append("")
                        lines.append(f"**Environment variable:** `CODESTORY_{full_name.upper().replace('.', '_')}`")
                        lines.append("")
                    
                    # Process nested properties
                    if "properties" in prop:
                        process_schema(prop, full_name)
        
        process_schema(schema["definitions"]["AppConfig"])
        return "\n".join(lines)
```

## Usage Examples

### Basic Usage

```python
from config import ConfigManager

# Load configuration from default locations
config_manager = ConfigManager()
config = config_manager.get_config()

# Access configuration values
db_type = config.storage.type
api_port = config.api.port

# Access configuration by path
db_type = config_manager.get_value("storage.type")
api_port = config_manager.get_value("api.port")
```

### Environment Variables

```bash
# Set configuration via environment variables
export CODESTORY_STORAGE_TYPE=neo4j
export CODESTORY_STORAGE_NEO4J_URI=bolt://localhost:7687
export CODESTORY_STORAGE_NEO4J_USER=neo4j
export CODESTORY_STORAGE_NEO4J_PASSWORD=password
export CODESTORY_API_PORT=9000
export CODESTORY_LOGGING_LEVEL=DEBUG

# Run the application
python -m codestory.main
```

### Configuration File

```yaml
# config.yaml
storage:
  type: sqlite
  sqlite_path: ./data/codestory.db

api:
  host: 0.0.0.0
  port: 8000
  debug: true

logging:
  level: INFO
  file: logs/codestory.log
```

### Generate Documentation

```python
from config import ConfigManager

config_manager = ConfigManager()
docs = config_manager.generate_documentation()

with open("config_docs.md", "w") as f:
    f.write(docs)
```

### Generate Environment File Template

```python
from config import ConfigManager

config_manager = ConfigManager()
config_manager.generate_env_file(".env.example")
```

## Integration with Components

Each component in the system receives its configuration section:

```python
from config import ConfigManager

# Component-specific initialization
def init_storage(config_manager):
    storage_config = config_manager.get_section("storage")
    
    if storage_config.type == "sqlite":
        return SqliteGraphStorage(
            db_path=storage_config.sqlite_path
        )
    elif storage_config.type == "neo4j":
        return Neo4jGraphStorage(
            uri=storage_config.neo4j_uri,
            user=storage_config.neo4j_user,
            password=storage_config.neo4j_password
        )
    else:
        raise ValueError(f"Unsupported storage type: {storage_config.type}")

# Application initialization
config_manager = ConfigManager()
storage = init_storage(config_manager)
```

## Command-Line Integration

The configuration system integrates with command-line arguments using argparse:

```python
import argparse
from config import ConfigManager

def setup_argparse():
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(description="Code Story")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    
    # Add command-specific subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Run API server")
    server_parser.add_argument("--host", help="API server host")
    server_parser.add_argument("--port", type=int, help="API server port")
    server_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    # Worker command
    worker_parser = subparsers.add_parser("worker", help="Run Celery worker")
    worker_parser.add_argument("--concurrency", type=int, help="Worker concurrency")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest repository")
    ingest_parser.add_argument("repo_path", help="Path to repository")
    ingest_parser.add_argument("--steps", help="Comma-separated list of steps to run")
    
    return parser

def main():
    """Main entry point."""
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Initialize configuration
    config_manager = ConfigManager(config_path=args.config)
    config = config_manager.get_config()
    
    # Apply command-line overrides
    if args.command == "server":
        if args.host:
            config.api.host = args.host
        if args.port:
            config.api.port = args.port
        if args.debug:
            config.api.debug = True
            
        # Run server with updated config
        from api.server import run_server
        run_server(config)
    
    elif args.command == "worker":
        # Run worker with config
        from worker.celery_app import run_worker
        run_worker(config)
    
    elif args.command == "ingest":
        # Run ingestion with config
        from ingestion.pipeline import run_pipeline
        
        steps = None
        if args.steps:
            steps = args.steps.split(",")
            
        run_pipeline(args.repo_path, steps=steps, config=config)
    
if __name__ == "__main__":
    main()
```

## Validation and Error Handling

The configuration system provides clear error messages for validation failures:

```
Configuration validation failed:
storage.neo4j_uri: neo4j_uri is required when type is 'neo4j'
storage.neo4j_user: neo4j_user is required when type is 'neo4j'
storage.neo4j_password: neo4j_password is required when type is 'neo4j'
```

## Testing

The configuration system can be easily mocked for testing:

```python
from config.schema import AppConfig, StorageConfig, ApiConfig

# Create test configuration
test_config = AppConfig(
    storage=StorageConfig(
        type="sqlite",
        sqlite_path=":memory:"  # In-memory database for testing
    ),
    api=ApiConfig(
        host="localhost",
        port=8000,
        debug=True
    )
)

# Pass to component under test
component = MyComponent(config=test_config)
```

## Best Practices

1. **Access by Section**: Components should receive only their relevant configuration section
2. **Use Default Values**: Always provide sensible defaults so minimal configuration is needed
3. **Validate Early**: Validate configuration at startup and provide clear error messages
4. **Document Options**: Use docstrings and comments to document configuration options
5. **Keep It Simple**: Don't make configuration more complex than necessary
6. **Avoid Direct Access**: Don't access configuration directly from components; use dependency injection
7. **Test with Different Configs**: Test components with different configuration values
8. **Generate Documentation**: Keep documentation up-to-date automatically

## Migrating from Old Configuration

The new configuration system replaces multiple sources of configuration:

1. **Docker Environment Variables**: Now managed via unified environment variables
2. **docker-compose.yml**: Settings moved to configuration files or environment variables
3. **Microservice Config Files**: Consolidated into a single configuration schema
4. **Command-Line Args**: Integrated through the argparse integration

Example mapping:

Old:
```
# docker-compose.yml
services:
  db:
    environment:
      NEO4J_AUTH: neo4j/password
  
  api:
    environment:
      NEO4J_URI: bolt://db:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: password
      API_PORT: 8000
```

New:
```yaml
# config.yaml
storage:
  type: neo4j
  neo4j_uri: bolt://localhost:7687
  neo4j_user: neo4j
  neo4j_password: password

api:
  port: 8000
```

Or with environment variables:
```bash
export CODESTORY_STORAGE_TYPE=neo4j
export CODESTORY_STORAGE_NEO4J_URI=bolt://localhost:7687
export CODESTORY_STORAGE_NEO4J_USER=neo4j
export CODESTORY_STORAGE_NEO4J_PASSWORD=password
export CODESTORY_API_PORT=8000
```

## Summary

The configuration system provides a flexible, consistent way to manage configuration across all components. It supports multiple configuration sources, validation, and clear error reporting. By centralizing configuration, it simplifies deployment and reduces the chance of configuration errors.
