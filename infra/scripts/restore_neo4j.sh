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
BACKUP_FILE=""
STORAGE_ACCOUNT=""
CONTAINER="neo4j-backups"
NEO4J_URI=""
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD=""
LIST_ONLY=false

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
        --backup-file)
            BACKUP_FILE="$2"
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
        --list-only)
            LIST_ONLY=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate storage account
if [ -z "$STORAGE_ACCOUNT" ]; then
    print_error "Azure Storage Account name is required. Provide it with --storage-account parameter."
    exit 1
fi

# List available backups
print_message "Listing available backups in storage account: $STORAGE_ACCOUNT, container: $CONTAINER"
AVAILABLE_BACKUPS=$(az storage blob list \
    --account-name "$STORAGE_ACCOUNT" \
    --container-name "$CONTAINER" \
    --query "[].{Name:name, CreatedOn:properties.creationTime}" \
    --output table \
    --auth-mode login)

echo "$AVAILABLE_BACKUPS"

# If list only, exit here
if [ "$LIST_ONLY" = true ]; then
    exit 0
fi

# Validate required parameters for restore
if [ -z "$BACKUP_FILE" ]; then
    print_error "Backup file is required. Provide it with --backup-file parameter."
    exit 1
fi

if [ -z "$NEO4J_URI" ]; then
    print_error "Neo4j URI is required. Provide it with --neo4j-uri parameter."
    exit 1
fi

if [ -z "$NEO4J_PASSWORD" ]; then
    print_error "Neo4j password is required. Provide it with --neo4j-password parameter."
    exit 1
fi

# Create temporary directory for restore
TEMP_DIR=$(mktemp -d)
print_message "Created temporary directory: $TEMP_DIR"

# Cleanup function
cleanup() {
    print_message "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

# Set up trap for cleanup on exit
trap cleanup EXIT

print_message "Starting Neo4j restore from backup: $BACKUP_FILE"
print_message "Neo4j URI: $NEO4J_URI"

# Download the backup from Azure Storage
print_message "Downloading backup from Azure Storage..."
az storage blob download \
    --account-name "$STORAGE_ACCOUNT" \
    --container-name "$CONTAINER" \
    --name "$BACKUP_FILE" \
    --file "$TEMP_DIR/$BACKUP_FILE" \
    --auth-mode login || {
    print_error "Failed to download backup from Azure Storage"
    exit 1
}

# Extract the backup
print_message "Extracting backup..."
tar -xzf "$TEMP_DIR/$BACKUP_FILE" -C "$TEMP_DIR" || {
    print_error "Failed to extract backup"
    exit 1
}

# Get Neo4j database information
print_message "Getting current Neo4j database information..."
CURRENT_DB_INFO=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
    "CALL db.schema.nodeTypeProperties() RETURN count(*) as NodeTypes") || {
    print_warning "Could not get current database information"
}

print_message "Current database node types: $CURRENT_DB_INFO"

# Request confirmation before proceeding
echo
echo "WARNING: This will restore the Neo4j database from backup, potentially overwriting existing data."
read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_message "Restore operation cancelled."
    exit 0
fi

# Perform the restore
print_message "Restoring Neo4j database..."

# First, clear the existing database
print_message "Clearing existing database..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
    "MATCH (n) DETACH DELETE n" || {
    print_error "Failed to clear existing database"
    exit 1
}

# Import the GraphML backup
print_message "Importing GraphML backup..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
    "CALL apoc.import.graphml('$TEMP_DIR/neo4j-backup.graphml', {readLabels: true})" || {
    print_error "Failed to import GraphML backup"
    exit 1
}

# Verify the restore
print_message "Verifying restore..."
RESTORED_DB_INFO=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
    "CALL db.schema.nodeTypeProperties() RETURN count(*) as NodeTypes") || {
    print_warning "Could not verify restored database"
}

print_message "Restored database node types: $RESTORED_DB_INFO"

print_message "Neo4j restore completed successfully!"