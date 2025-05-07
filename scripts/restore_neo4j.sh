#!/bin/bash

# Script to restore Neo4j database from backup
# This script restores a Neo4j database backup using the neo4j-admin tool

set -e

# Default values
BACKUP_DIR="./backups"
CONTAINER_NAME="codestory-neo4j"
BACKUP_NAME=""

# Process command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dir)
      BACKUP_DIR="$2"
      shift 2
      ;;
    --name)
      BACKUP_NAME="$2"
      shift 2
      ;;
    --container)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if backup name is provided
if [[ -z "${BACKUP_NAME}" ]]; then
    echo "Error: Backup name must be provided with --name"
    echo "Usage: $0 --name <backup_name> [--dir <backup_dir>] [--container <container_name>]"
    exit 1
fi

# Check if backup exists
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
if [[ ! -d "${BACKUP_PATH}" ]]; then
    echo "Error: Backup not found at ${BACKUP_PATH}"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if container is running
if ! docker ps | grep -q ${CONTAINER_NAME}; then
    echo "Error: Neo4j container '${CONTAINER_NAME}' is not running"
    exit 1
fi

echo "Restoring Neo4j database from backup: ${BACKUP_NAME}"

# Stop Neo4j service in the container
echo "Stopping Neo4j service..."
docker exec ${CONTAINER_NAME} neo4j stop

# Create a restore directory inside the container
docker exec ${CONTAINER_NAME} mkdir -p /var/lib/neo4j/restore

# Copy the backup to the container
docker cp "${BACKUP_PATH}" ${CONTAINER_NAME}:/var/lib/neo4j/restore/neo4j

# Run the restore
echo "Restoring database..."
docker exec ${CONTAINER_NAME} neo4j-admin database restore \
    --from=/var/lib/neo4j/restore/neo4j \
    --database=neo4j \
    --force

# Clean up restore in container
docker exec ${CONTAINER_NAME} rm -rf /var/lib/neo4j/restore

# Start Neo4j service
echo "Starting Neo4j service..."
docker exec ${CONTAINER_NAME} neo4j start

echo "Waiting for Neo4j to start..."
sleep 10

# Check if Neo4j is running
echo "Verifying Neo4j is running..."
docker exec ${CONTAINER_NAME} neo4j status

echo "Restore completed successfully."
echo "Neo4j database has been restored from: ${BACKUP_PATH}"