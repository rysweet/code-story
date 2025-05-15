#!/bin/bash
# Script to mount a repository for ingestion by CodeStory

# Display help info
if [ "$1" == "-h" ] || [ "$1" == "--help" ] || [ -z "$1" ]; then
    echo "Usage: $0 /path/to/repository"
    echo ""
    echo "This script sets up environment variables for docker-compose to mount"
    echo "a repository directory into the CodeStory containers for ingestion."
    echo ""
    echo "Example:"
    echo "  $0 /home/user/my-project"
    echo ""
    exit 0
fi

# Get the absolute path of the repository
REPO_PATH=$(realpath "$1")

# Check if the path exists and is a directory
if [ ! -d "$REPO_PATH" ]; then
    echo "Error: $REPO_PATH is not a valid directory"
    exit 1
fi

# Export the environment variable for docker-compose
export REPOSITORY_PATH="$REPO_PATH"

echo "Repository path set to: $REPOSITORY_PATH"
echo "This repository will be mounted at /repositories in the containers."
echo ""
echo "To run docker-compose with this repository mounted, use:"
echo "REPOSITORY_PATH=\"$REPO_PATH\" docker-compose up -d"
echo ""
echo "Alternatively, in your current shell, the REPOSITORY_PATH variable has been exported,"
echo "so you can simply run: docker-compose up -d"
echo ""
echo "When using the CLI to ingest this repository, use the path:"
echo "/repositories/$(basename \"$REPO_PATH\")"