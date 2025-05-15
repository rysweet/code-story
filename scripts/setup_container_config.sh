#!/bin/bash
# This script ensures that the .codestory.container.toml file exists
# before starting the worker container.

set -e

# Path to the default and container configuration files
DEFAULT_CONFIG=".codestory.default.toml"
CONTAINER_CONFIG=".codestory.container.toml"
PROJECT_DIR=$(pwd)

# Check if container config exists, if not create it from default
if [ ! -f "$PROJECT_DIR/$CONTAINER_CONFIG" ]; then
    echo "Container configuration file not found, creating from default..."
    if [ -f "$PROJECT_DIR/$DEFAULT_CONFIG" ]; then
        cp "$PROJECT_DIR/$DEFAULT_CONFIG" "$PROJECT_DIR/$CONTAINER_CONFIG"
        
        # Update the config file with container-specific settings
        sed -i.bak 's/uri = "bolt:\/\/localhost:[0-9]\+"/uri = "bolt:\/\/neo4j:7687"/' "$PROJECT_DIR/$CONTAINER_CONFIG"
        sed -i.bak 's/uri = "redis:\/\/localhost:[0-9]\+"/uri = "redis:\/\/redis:6379"/' "$PROJECT_DIR/$CONTAINER_CONFIG"
        
        echo "Container configuration created successfully."
    else
        echo "Default configuration file not found. Creating minimal configuration..."
        cat > "$PROJECT_DIR/$CONTAINER_CONFIG" << EOF
[general]
app_name = "code-story"
version = "0.1.0"
environment = "development"
log_level = "INFO"

[neo4j]
uri = "bolt://neo4j:7687"
username = "neo4j"
password = "password"
database = "neo4j"

[redis]
uri = "redis://redis:6379"

[service]
host = "0.0.0.0"
port = 8000
dev_mode = true
EOF
        echo "Minimal container configuration created."
    fi
else
    echo "Container configuration file already exists."
fi

# Ensure proper permissions
chmod 644 "$PROJECT_DIR/$CONTAINER_CONFIG"

echo "Container configuration checked and ready."