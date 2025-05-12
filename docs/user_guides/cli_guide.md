# CLI Guide

The Code Story Command Line Interface (CLI) provides a powerful way to interact with the system from your terminal. This guide covers the installation, basic usage, and available commands.

## Installation

The CLI is automatically installed when you install Code Story:

```bash
# Install Code Story with Poetry
poetry install

# Or use pip
pip install codestory
```

After installation, you can access the CLI using either `codestory` or the shorthand `cs`:

```bash
# Both commands work the same way
codestory --help
cs --help
```

## Basic Usage

The CLI follows this basic structure:

```bash
cs [OPTIONS] COMMAND [ARGS]...
```

### Global Options

These options can be used with any command:

| Option | Description |
|--------|-------------|
| `--config FILE` | Path to configuration file (defaults to `.codestory.toml`) |
| `--verbose` | Enable verbose output for debugging |
| `--no-color` | Disable colorized output |
| `--help` | Show help message and exit |

## Available Commands

### Configuration Management

```bash
# List all configuration settings
cs config list

# Set a configuration value
cs config set neo4j.uri neo4j://localhost:7687

# Get a specific configuration value
cs config get neo4j.uri

# Export configuration to a file
cs config export --format json --output config.json
```

### Service Management

```bash
# Check service status
cs service status

# Start all services
cs service start

# Stop all services
cs service stop

# Restart services
cs service restart
```

### Ingestion

```bash
# Ingest a repository
cs ingest /path/to/repo

# Ingest a specific branch
cs ingest /path/to/repo --branch main

# Ingest with selected steps
cs ingest /path/to/repo --steps filesystem,summarizer

# List active and completed jobs
cs ingest list

# Check status of a specific job
cs ingest status JOB_ID
```

### Querying

```bash
# Search for entities by name pattern
cs query search "class*Controller"

# Find code similar to a file
cs query similar /path/to/file.py

# Get details about a specific node
cs query node NODE_ID

# Execute a custom Cypher query
cs query cypher "MATCH (n:Class) RETURN n.name LIMIT 10"
```

### Visualization

```bash
# Generate a visualization of the entire graph
cs visualize graph

# Visualize dependencies for a specific file
cs visualize dependencies /path/to/file.py

# Visualize the class hierarchy
cs visualize classes

# Visualize a custom subgraph
cs visualize custom "MATCH p=(c:Class)-[:IMPLEMENTS]->(i:Interface) RETURN p"
```

### Natural Language Queries

```bash
# Ask a question about the codebase
cs ask "How does the authentication system work?"

# Ask with context from a specific file
cs ask "What does this function do?" --context /path/to/file.py:123-150
```

## Examples

### Basic Workflow

```bash
# Start the services
cs service start

# Ingest a repository
cs ingest /path/to/my-project
# Job ID: 3f7a2d9e-5b1c-4c07-8f7d-a6b3c4d5e6f7

# Check ingestion status
cs ingest status 3f7a2d9e-5b1c-4c07-8f7d-a6b3c4d5e6f7

# Generate a visualization
cs visualize graph --output graph.html

# Ask a question about the codebase
cs ask "What are the main components in this project?"
```

### Working with Configuration

```bash
# View current configuration
cs config list

# Change the Neo4j password
cs config set neo4j.password new-password

# Use a custom OpenAI model
cs config set llm.model gpt-4

# Export configuration to share with team (excluding secrets)
cs config export --format yaml --output team-config.yaml --no-secrets
```

### Advanced Querying

```bash
# Find all controllers with more than 5 methods
cs query cypher "MATCH (c:Class)-[:CONTAINS]->(m:Method) WHERE c.name CONTAINS 'Controller' WITH c, COUNT(m) as methods WHERE methods > 5 RETURN c.name, methods ORDER BY methods DESC"

# Find files that import a specific module
cs query cypher "MATCH (f:File)-[:IMPORTS]->(m:Module) WHERE m.name = 'logging' RETURN f.name"

# Find methods that use a specific database table
cs query search "SELECT.*FROM users" --node-type Method
```

## Environment Variables

The CLI respects the following environment variables:

| Variable | Description |
|----------|-------------|
| `CODESTORY_CONFIG_PATH` | Path to configuration file |
| `CODESTORY_SERVICE_URL` | URL of the Code Story service |
| `CODESTORY_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CODESTORY_NO_COLOR` | Disable colorized output if set to "1" |

## Tab Completion

Enable tab completion for your shell:

```bash
# Bash
cs --install-completion bash

# Zsh
cs --install-completion zsh

# Fish
cs --install-completion fish
```

## Troubleshooting

If you encounter any issues with the CLI:

1. Ensure the Code Story service is running:
   ```bash
   cs service status
   ```

2. Check the connection settings:
   ```bash
   cs config get service.url
   ```

3. Enable verbose output for detailed logs:
   ```bash
   cs --verbose ingest status JOB_ID
   ```

4. Reset the configuration if needed:
   ```bash
   cs config reset
   ```

For more detailed information, please refer to the [API Reference](../api/index.md) documentation.