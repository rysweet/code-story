# Configuration Guide

Code Story uses a layered configuration system to make it easy to adapt the system to different environments.

## Configuration Sources

Configuration settings are loaded from multiple sources in the following order of precedence:

1. **Environment variables** (highest precedence)
2. **.env file** (user-specific bootstrap settings)
3. **.codestory.toml file** (application settings)
4. **Default values** (lowest precedence)

## Essential Bootstrap Settings (.env)

The `.env` file contains essential bootstrap settings needed to connect to required services. This file should be edited directly by users when setting up the system for the first time or when changing environments.

Copy the template file to create your own configuration:

```bash
cp .env.template .env
```

Edit the file to include your specific connection information:

```
# Core connectivity settings
NEO4J__URI=bolt://localhost:7687
NEO4J__USERNAME=neo4j
NEO4J__PASSWORD=password

# Redis settings
REDIS__URI=redis://localhost:6379

# Service settings
SERVICE__HOST=localhost
SERVICE__PORT=8000

# OpenAI settings
OPENAI__API_KEY=your-api-key-here
```

### Environment Variables Format

Environment variables use double underscores (`__`) as delimiters for nested settings:

- `NEO4J__URI` maps to `neo4j.uri` in the settings model
- `SERVICE__HOST` maps to `service.host` in the settings model

## Application Settings (.codestory.toml)

The `.codestory.toml` file contains comprehensive application settings. Instead of editing this file directly, use the CLI's `config` commands to manage these settings:

```bash
# Show current configuration
codestory config show

# Update a configuration value
codestory config set neo4j.connection_timeout=60

# Edit all configuration in an editor
codestory config edit
```

Example `.codestory.toml` file:

```toml
[general]
app_name = "code-story"
description = "A system to convert codebases into richly-linked knowledge graphs with natural-language summaries"
version = "0.1.0"
environment = "development"
log_level = "INFO"
auth_enabled = false

[neo4j]
connection_timeout = 30
max_connection_pool_size = 50
connection_acquisition_timeout = 60
auto_initialize_schema = true
force_schema_update = true

[openai]
embedding_model = "text-embedding-3-small"
chat_model = "gpt-4o"
reasoning_model = "gpt-4o"
max_retries = 3
retry_backoff_factor = 2.0
temperature = 0.1
max_tokens = 4096

# Additional sections...
```

## Configuration in Docker Environments

When running in Docker Compose, use the following settings in your `.env` file:

```
# Docker container networking
NEO4J__URI=bolt://neo4j:7687
REDIS__URI=redis://redis:6379
SERVICE__HOST=0.0.0.0
```

The CLI will automatically detect if you're connecting from outside Docker and map the service names to localhost with appropriate ports.

## Configuration Model

The configuration system uses Pydantic models to validate settings and provide type safety. All settings are organized into nested sections:

- `neo4j`: Neo4j database connection settings
- `redis`: Redis connection settings 
- `openai`: OpenAI API settings
- `azure_openai`: Azure OpenAI API settings
- `service`: Service configuration settings
- `ingestion`: Ingestion pipeline settings
- `plugins`: Plugin settings
- `telemetry`: Telemetry settings
- `interface`: Interface settings for GUI and CLI

## Environment-Specific Configuration

You can create different environment-specific configurations by:

1. Creating separate `.env` files (e.g., `.env.dev`, `.env.prod`)
2. Specifying which to use via the `CODESTORY_CONFIG_FILE` environment variable:

```bash
CODESTORY_CONFIG_FILE=.env.prod codestory service start
```

## Secure Handling of Sensitive Values

Sensitive values (e.g., passwords, API keys) are:

1. Masked in the CLI output (unless `--sensitive` flag is used)
2. Stored securely in memory using Pydantic's `SecretStr` type 
3. Never logged or exposed in error messages

For production deployments, consider using Azure KeyVault integration by setting:

```
AZURE__KEYVAULT_NAME=your-keyvault-name
```

This allows automatic loading of secrets from KeyVault for sensitive fields.