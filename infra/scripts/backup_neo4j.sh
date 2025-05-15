#!/bin/bash
set -e

# Colors for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
BACKUP_NAME="neo4j-backup-$(date +%Y%m%d-%H%M%S)"
STORAGE_ACCOUNT=""
CONTAINER="neo4j-backups"
NEO4J_URI=""
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD=""
RETENTION_DAYS=30

# Process command-line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --neo4j-uri)
            NEO4J_URI="$2"
            shift 2
            ;;
        --neo4j-username)
            NEO4J_USERNAME="$2"
            shift 2
            ;;
        --neo4j-password)
            NEO4J_PASSWORD="$2"
            shift 2
            ;;
        --backup-name)
            BACKUP_NAME="$2"
            shift 2
            ;;
        --storage-account)
            STORAGE_ACCOUNT="$2"
            shift 2
            ;;
        --container)
            CONTAINER="$2"
            shift 2
            ;;
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$NEO4J_URI" ]; then
    print_error "Neo4j URI is required. Provide it with --neo4j-uri parameter."
    exit 1
fi

if [ -z "$NEO4J_PASSWORD" ]; then
    print_error "Neo4j password is required. Provide it with --neo4j-password parameter."
    exit 1
fi

if [ -z "$STORAGE_ACCOUNT" ]; then
    print_error "Azure Storage Account name is required. Provide it with --storage-account parameter."
    exit 1
fi

# Create temporary directory for backup
TEMP_DIR=$(mktemp -d)
print_message "Created temporary directory: $TEMP_DIR"

# Cleanup function
cleanup() {
    print_message "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

# Set up trap for cleanup on exit
trap cleanup EXIT

print_message "Starting Neo4j backup: $BACKUP_NAME"
print_message "Neo4j URI: $NEO4J_URI"
print_message "Storage Account: $STORAGE_ACCOUNT"
print_message "Container: $CONTAINER"

# Perform Neo4j dump
print_message "Performing Neo4j dump..."
NEO4J_HOST=$(echo "$NEO4J_URI" | sed -E 's|^bolt://||;s|:[0-9]+$||')
NEO4J_PORT=$(echo "$NEO4J_URI" | grep -oE ':[0-9]+$' | sed 's/://')

# Run the Neo4j dump command
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
    "CALL apoc.export.graphml.all('$TEMP_DIR/neo4j-backup.graphml', {})" || {
    print_error "Failed to perform Neo4j dump"
    exit 1
}

# Compress the backup
print_message "Compressing backup..."
tar -czf "$TEMP_DIR/$BACKUP_NAME.tar.gz" -C "$TEMP_DIR" neo4j-backup.graphml || {
    print_error "Failed to compress backup"
    exit 1
}

# Upload to Azure Storage
print_message "Uploading backup to Azure Storage..."
az storage blob upload \
    --account-name "$STORAGE_ACCOUNT" \
    --container-name "$CONTAINER" \
    --name "$BACKUP_NAME.tar.gz" \
    --file "$TEMP_DIR/$BACKUP_NAME.tar.gz" \
    --auth-mode login || {
    print_error "Failed to upload backup to Azure Storage"
    exit 1
}

# Clean up old backups
print_message "Cleaning up backups older than $RETENTION_DAYS days..."
CUTOFF_DATE=$(date -d "-$RETENTION_DAYS days" +%Y-%m-%d)

az storage blob list \
    --account-name "$STORAGE_ACCOUNT" \
    --container-name "$CONTAINER" \
    --query "[?properties.creationTime < '$CUTOFF_DATE'].name" \
    --output tsv | while read -r blob_name; do
    
    if [ ! -z "$blob_name" ]; then
        print_message "Deleting old backup: $blob_name"
        az storage blob delete \
            --account-name "$STORAGE_ACCOUNT" \
            --container-name "$CONTAINER" \
            --name "$blob_name" \
            --auth-mode login || {
            print_warning "Failed to delete old backup: $blob_name"
        }
    fi
done

print_message "Neo4j backup completed successfully: $BACKUP_NAME"
print_message "Backup stored in storage account: $STORAGE_ACCOUNT, container: $CONTAINER"