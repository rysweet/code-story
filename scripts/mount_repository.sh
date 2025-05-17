#!/bin/bash
# Script to mount a repository for ingestion by CodeStory

# Display help info
if [ "$1" == "-h" ] || [ "$1" == "--help" ] || [ -z "$1" ]; then
    echo "Usage: $0 /path/to/repository [--restart]"
    echo ""
    echo "This script sets up environment variables for docker-compose to mount"
    echo "a repository directory into the CodeStory containers for ingestion."
    echo ""
    echo "Options:"
    echo "  --restart       Restart containers after mounting (requires docker-compose)"
    echo ""
    echo "Example:"
    echo "  $0 /home/user/my-project"
    echo "  $0 /home/user/my-project --restart"
    echo ""
    exit 0
fi

# Check for the restart flag
RESTART=false
REPO_ARG="$1"
if [ "$2" == "--restart" ]; then
    RESTART=true
fi
if [ "$1" == "--restart" ] && [ ! -z "$2" ]; then
    RESTART=true
    REPO_ARG="$2"
fi

# Get the absolute path of the repository
REPO_PATH=$(realpath "$REPO_ARG")

# Check if the path exists and is a directory
if [ ! -d "$REPO_PATH" ]; then
    echo "Error: $REPO_PATH is not a valid directory"
    exit 1
fi

# Export the environment variable for docker-compose
export REPOSITORY_PATH="$REPO_PATH"

# Create a marker file in the repository to indicate it's mounted
# This helps the CLI detect that we're using container mode
REPO_CONFIG_DIR="$REPO_PATH/.codestory"
mkdir -p "$REPO_CONFIG_DIR"

# Create repository config file
REPO_CONFIG_FILE="$REPO_CONFIG_DIR/repository.toml"
cat > "$REPO_CONFIG_FILE" <<EOL
# CodeStory repository configuration
# Created by mount_repository.sh

[repository]
name = "$(basename "$REPO_PATH")"
local_path = "$REPO_PATH"
container_path = "/repositories/$(basename "$REPO_PATH")"
mounted = true
mount_time = "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
EOL

echo "Repository path set to: $REPOSITORY_PATH"
echo "This repository will be mounted at /repositories in the containers."
echo "Repository config created at: $REPO_CONFIG_FILE"
echo ""

# If restart flag is set, restart containers
if [ "$RESTART" = true ]; then
    echo "Restarting containers with mounted repository..."
    docker-compose down
    REPOSITORY_PATH="$REPO_PATH" docker-compose up -d
    
    # Wait for services to come up
    echo "Waiting for services to start..."
    sleep 5
    
    # Check if service is healthy
    ATTEMPTS=0
    MAX_ATTEMPTS=30
    SERVICE_HEALTHY=false
    
    while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
        ATTEMPTS=$((ATTEMPTS+1))
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' codestory-service 2>/dev/null || echo "not found")
        
        if [ "$HEALTH" == "healthy" ]; then
            SERVICE_HEALTHY=true
            break
        fi
        
        echo "Service status: $HEALTH (attempt $ATTEMPTS/$MAX_ATTEMPTS)"
        sleep 5
    done
    
    if [ "$SERVICE_HEALTHY" = true ]; then
        echo "Services are ready!"
    else
        echo "Services may not be fully ready yet. Check status with 'docker ps'."
    fi
else
    echo "To run docker-compose with this repository mounted, use:"
    echo "REPOSITORY_PATH=\"$REPO_PATH\" docker-compose up -d"
    echo ""
    echo "Alternatively, in your current shell, the REPOSITORY_PATH variable has been exported,"
    echo "so you can simply run: docker-compose up -d"
    echo ""
    echo "To restart containers with the new repository mount, use:"
    echo "$0 \"$REPO_PATH\" --restart"
    echo ""
fi

echo "To start ingestion of the repository with the CLI, run:"
echo "codestory ingest start \"$REPO_PATH\" --container"
echo ""
echo "The CLI will automatically map your local path to the container path:"
echo "Local:     $REPO_PATH"
echo "Container: /repositories/$(basename "$REPO_PATH")"