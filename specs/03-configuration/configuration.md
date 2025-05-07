# 3.0 Configuration Module

**Previous:** [Scaffolding](../02-scaffolding/scaffolding.md) | **Next:** [Graph Database Service](../04-graph-database/graph-database.md)

**Dependencies:** [Scaffolding](../02-scaffolding/scaffolding.md) 

**Used by:** 
- [Graph Database Service](../04-graph-database/graph-database.md)
- [AI Client](../05-ai-client/ai-client.md)
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)
- [Code Story Service](../11-code-story-service/code-story-service.md)
- [MCP Adapter](../12-mcp-adapter/mcp-adapter.md)
- [CLI](../13-cli/cli.md)
- [GUI](../14-gui/gui.md)

## 3.1 Purpose

Provide a centralized configuration system that loads settings from multiple sources with clear precedence rules, exposes a strongly-typed settings interface to all application components, and handles sensitive values securely. The configuration module is the foundation for all other components, enabling consistent access to settings across the application.

## 3.2 Responsibilities

- Load configuration from multiple sources with defined precedence: environment variables > `.env` file > `.codestory.toml` > hard-coded defaults
- Expose a strongly-typed configuration interface via Pydantic models to all application components
- Provide secure handling of sensitive values with Azure KeyVault integration
- Support hot-reloading of configuration for selected settings without service restart
- Enable component-specific configuration sections with inheritance and overrides
- Validate configuration values and provide helpful error messages
- Support persistence of configuration changes back to `.env` and `.codestory.toml`
- Implement the Singleton pattern to ensure consistent configuration across the application

## 3.3 Configuration Schema

The configuration is organized hierarchically with sections for each major component:

```python
class Settings(BaseSettings):
    # Core settings
    app_name: str = "code-story"
    environment: Literal["development", "testing", "production"] = "development"
    log_level: str = "INFO"
    
    # Database settings
    neo4j: Neo4jSettings
    redis: RedisSettings
    
    # Authentication
    auth_enabled: bool = False  # --no-auth flag for local development
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    
    # Azure KeyVault
    azure_keyvault_name: Optional[str] = None
    
    # OpenAI
    openai: OpenAISettings
    
    # Ingestion pipeline
    ingestion: IngestionSettings
    
    # GUI & CLI
    interface: InterfaceSettings
    
    # Service endpoints
    service: ServiceSettings
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False
        
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            return (
                env_settings,                      # 1. Environment variables
                init_settings,                     # 2. Initialization values
                file_secret_settings,              # 3. .env file
                cls._toml_config,                  # 4. .codestory.toml
                cls._keyvault_settings,            # 5. Azure KeyVault (only for marked fields)
            )
        
        @classmethod
        def _toml_config(cls, settings):
            # Load settings from .codestory.toml
            pass
            
        @classmethod
        def _keyvault_settings(cls, settings):
            # Load secrets from Azure KeyVault if configured
            pass
```

Component-specific settings classes that inherit from Pydantic's `BaseSettings`:

```python
class Neo4jSettings(BaseSettings):
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: SecretStr = SecretStr("password")  # Marked for KeyVault resolution
    connection_timeout: int = 30
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60
    
class OpenAISettings(BaseSettings):
    endpoint: str = "https://api.openai.com/v1"
    api_key: SecretStr  # Marked for KeyVault resolution
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o"
    reasoning_model: str = "gpt-4o"
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    
class IngestionSettings(BaseSettings):
    config_path: str = "pipeline_config.yml"
    steps: Dict[str, Dict[str, Any]] = {}  # Step-specific configuration
    max_retries: int = 3
    concurrency: int = 5
```

## 3.4 Implementation Details

### 3.4.1 Singleton Pattern

```python
# src/codestory/config/settings.py
from functools import lru_cache
from pydantic import BaseSettings

class Settings(BaseSettings):
    # ... as defined above ...
    pass

@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of the Settings."""
    return Settings()
```

### 3.4.2 Azure KeyVault Integration

For secure values (marked with `SecretStr`), the configuration module can load values from Azure KeyVault when `AZURE_KEYVAULT_NAME` is set:

```python
def load_from_keyvault(settings):
    """Load secret values from Azure KeyVault."""
    if not settings.azure_keyvault_name:
        return settings
        
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    
    credential = DefaultAzureCredential()
    client = SecretClient(
        vault_url=f"https://{settings.azure_keyvault_name}.vault.azure.net/", 
        credential=credential
    )
    
    # Example of resolving a secret
    if not settings.neo4j.password.get_secret_value():
        secret = client.get_secret("neo4j-password")
        settings.neo4j.password = SecretStr(secret.value)
    
    return settings
```

### 3.4.3 Configuration Persistence

```python
# src/codestory/config/writer.py
import os
import toml
from typing import Dict, Any, Optional
from dotenv import set_key

def update_env(key: str, value: str, env_file: str = '.env'):
    """Update a value in the .env file."""
    set_key(env_file, key, value)

def update_toml(section: str, key: str, value: Any, toml_file: str = '.codestory.toml'):
    """Update a value in the .codestory.toml file."""
    try:
        config = toml.load(toml_file) if os.path.exists(toml_file) else {}
    except Exception:
        config = {}
    
    if section not in config:
        config[section] = {}
    
    config[section][key] = value
    
    with open(toml_file, 'w') as f:
        toml.dump(config, f)

def update_config(section: str, key: str, value: Any, persist_to: str = 'env'):
    """Update configuration in memory and optionally persist to file."""
    from .settings import get_settings
    
    # Update in-memory settings
    settings = get_settings()
    if hasattr(settings, section) and hasattr(getattr(settings, section), key):
        setattr(getattr(settings, section), key, value)
    
    # Persist to file if requested
    if persist_to == 'env':
        update_env(f"{section.upper()}_{key.upper()}", str(value))
    elif persist_to == 'toml':
        update_toml(section, key, value)
```

### 3.4.4 Configuration Access Example

```python
# Example usage in another module
from codestory.config.settings import get_settings

def connect_to_neo4j():
    settings = get_settings()
    
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        settings.neo4j.uri,
        auth=(settings.neo4j.username, settings.neo4j.password.get_secret_value()),
        max_connection_pool_size=settings.neo4j.max_connection_pool_size
    )
    return driver
```

## 3.5 Example Configuration Files

### 3.5.1 .env-template Example

```
# Core settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Neo4j settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Redis settings
REDIS_URI=redis://localhost:6379/0

# Azure OpenAI
OPENAI_ENDPOINT=https://your-resource.openai.azure.com
OPENAI_API_KEY=your-api-key-here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_REASONING_MODEL=gpt-4o

# Authentication (for production)
# AUTH_ENABLED=true
# AZURE_TENANT_ID=your-tenant-id
# AZURE_CLIENT_ID=your-client-id

# Azure KeyVault (uncomment to use)
# AZURE_KEYVAULT_NAME=your-keyvault-name
```

### 3.5.2 .codestory.toml Example

```toml
[neo4j]
connection_timeout = 30
max_connection_pool_size = 50
connection_acquisition_timeout = 60

[openai]
max_retries = 3
retry_backoff_factor = 2.0

[ingestion]
config_path = "pipeline_config.yml"
max_retries = 3
concurrency = 5

# Step-specific configuration
[ingestion.steps.blarify]
timeout = 300
docker_image = "codestory/blarify:latest"

[ingestion.steps.filesystem]
ignore_patterns = ["node_modules/", ".git/", "__pycache__/"]

[ingestion.steps.summarizer]
max_concurrency = 5
max_tokens_per_file = 8000

[service]
host = "0.0.0.0"
port = 8000
workers = 4
```

## 3.6 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to access configuration values through a consistent interface so that I can configure components without worrying about implementation details. | • Configuration is accessible through the `get_settings()` function.<br>• Settings are strongly-typed with appropriate defaults.<br>• Settings are validated on load with helpful error messages for invalid values.<br>• The settings object is immutable to prevent unexpected changes. |
| As a developer, I want to store configuration in different sources with clear precedence rules so that I can override settings for different environments. | • Environment variables take precedence over file-based settings.<br>• `.env` file takes precedence over `.codestory.toml`.<br>• Hard-coded defaults are used as a last resort.<br>• The configuration system correctly merges settings from all sources. |
| As a developer, I want to manage sensitive configuration values securely so that I don't expose secrets in code or configuration files. | • Sensitive values are marked with `SecretStr` and redacted in logs and errors.<br>• Azure KeyVault integration works when configured.<br>• Secrets can be stored in environment variables or `.env` file.<br>• Secret values are only accessible through controlled methods. |
| As a developer, I want to be able to update configuration at runtime and have changes persist so that I can adjust settings without restarting the application. | • The configuration can be updated programmatically.<br>• Changes can be persisted to `.env` or `.codestory.toml` files.<br>• The configuration module provides methods for safely writing configuration changes.<br>• Components can observe configuration changes when relevant. |
| As a developer, I want to organize configuration into logical sections so that component-specific settings can be managed together. | • Configuration is organized into component-specific sections.<br>• Each section has its own Pydantic model.<br>• Components can access only their relevant configuration sections.<br>• The structure is reflected in file-based configuration. |
| As a developer, I want comprehensive documentation and examples so that I can understand how to use the configuration system effectively. | • The configuration module is fully documented with docstrings.<br>• Example configuration files are provided.<br>• Usage examples show how to access and update settings.<br>• Documentation explains how settings are resolved from different sources. |

## 3.7 Testing Strategy

* **Unit tests** - Verify loading from different sources, precedence rules, type validation, and KeyVault integration.
* **Integration tests** - Verify interaction with actual files and environment variables.

## 3.8 Implementation Steps

1. **Create basic settings models**
   - Implement `Settings` base class with all required fields
   - Define component-specific settings models
   - Set up Pydantic model validation

2. **Implement multi-source loading**
   - Environment variables loader
   - `.env` file loader
   - `.codestory.toml` loader
   - Default values fallback

3. **Add Azure KeyVault integration**
   - Implement secret resolution from KeyVault
   - Add mechanism to mark fields for KeyVault resolution
   - Handle authentication with DefaultAzureCredential

4. **Create persistence mechanism**
   - Implement `.env` file writer
   - Implement `.codestory.toml` file writer
   - Add safety checks for file writing

5. **Implement configuration singleton**
   - Set up caching with lru_cache
   - Ensure thread safety
   - Add refresh mechanism for hot reloading

6. **Add comprehensive error handling**
   - Custom validation errors
   - Helpful error messages
   - Fallback strategies

7. **Write comprehensive tests**
   - Unit tests for each component
   - Integration tests for file operations
   - Mock tests for Azure KeyVault

8. **Create example configurations**
   - `.env-template` with commented explanations
   - Example `.codestory.toml`
   - Documentation with usage examples

9. **Implement configuration documentation**
   - Add comprehensive docstrings
   - Generate API documentation
   - Create usage examples
   - Document error handling strategies

10. **Verification and Review**
   - Run all unit and integration tests to ensure complete functionality
   - Verify test coverage meets targets (≥90% for critical modules)
   - Run linting and type checking (`ruff check` and `mypy --strict`) 
   - Perform thorough code review against all requirements and user stories
   - Validate configuration loading from all sources
   - Test edge cases and error handling
   - Make necessary adjustments based on review findings
   - Re-run all tests after any changes
   - Document any discovered issues and their resolutions
   - Create detailed PR for final review
---

