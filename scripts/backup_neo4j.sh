#!/bin/bash

# Script to backup Neo4j database
# This script creates a backup of the Neo4j database using the neo4j-admin tool

set -e

# Default values
BACKUP_DIR="./backups"
CONTAINER_NAME="codestory-neo4j"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="neo4j_backup_${TIMESTAMP}"

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

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo "Creating backup of Neo4j database: ${BACKUP_NAME}"
echo "Backup will be stored in: ${BACKUP_DIR}"

# Check if container is running
if ! docker ps | grep -q ${CONTAINER_NAME}; then
    echo "Error: Neo4j container '${CONTAINER_NAME}' is not running"
    exit 1
fi

# Create a backup directory inside the container
docker exec ${CONTAINER_NAME} mkdir -p /var/lib/neo4j/backups

# Run the backup
docker exec ${CONTAINER_NAME} neo4j-admin database backup \
    --backup-dir=/var/lib/neo4j/backups \
    --database=neo4j

# Copy the backup from the container to the host
docker cp ${CONTAINER_NAME}:/var/lib/neo4j/backups/neo4j "${BACKUP_DIR}/${BACKUP_NAME}"

# Clean up backup in container
docker exec ${CONTAINER_NAME} rm -rf /var/lib/neo4j/backups/neo4j

echo "Backup completed successfully: ${BACKUP_DIR}/${BACKUP_NAME}"
echo "Use restore_neo4j.sh to restore this backup if needed"