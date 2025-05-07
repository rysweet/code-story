#!/bin/bash

# Script to import data into Neo4j database
# This script imports data from CSV or JSON files using Cypher or neo4j-admin import

set -e

# Default values
IMPORT_DIR="./imports"
CONTAINER_NAME="codestory-neo4j"
IMPORT_MODE="cypher"  # Options: cypher, admin
FILE_FORMAT="csv"     # Options: csv, json

# Process command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dir)
      IMPORT_DIR="$2"
      shift 2
      ;;
    --mode)
      IMPORT_MODE="$2"
      shift 2
      ;;
    --format)
      FILE_FORMAT="$2"
      shift 2
      ;;
    --container)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    --script)
      CYPHER_SCRIPT="$2"
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

# Check if container is running
if ! docker ps | grep -q ${CONTAINER_NAME}; then
    echo "Error: Neo4j container '${CONTAINER_NAME}' is not running"
    exit 1
fi

# Validate import mode
if [[ "${IMPORT_MODE}" != "cypher" && "${IMPORT_MODE}" != "admin" ]]; then
    echo "Error: Import mode must be 'cypher' or 'admin'"
    exit 1
fi

# Validate file format
if [[ "${FILE_FORMAT}" != "csv" && "${FILE_FORMAT}" != "json" ]]; then
    echo "Error: File format must be 'csv' or 'json'"
    exit 1
fi

# Create import directory inside the container
docker exec ${CONTAINER_NAME} mkdir -p /var/lib/neo4j/import/data

# Copy import files to the container
echo "Copying import files to container..."
docker cp "${IMPORT_DIR}/." ${CONTAINER_NAME}:/var/lib/neo4j/import/data/

# Import based on the selected mode
if [[ "${IMPORT_MODE}" == "cypher" ]]; then
    # Import using Cypher script
    if [[ -n "${CYPHER_SCRIPT}" ]]; then
        echo "Importing data using Cypher script: ${CYPHER_SCRIPT}"
        docker cp "${CYPHER_SCRIPT}" ${CONTAINER_NAME}:/var/lib/neo4j/import/import_script.cypher
        docker exec ${CONTAINER_NAME} cypher-shell -u neo4j -p password -f /var/lib/neo4j/import/import_script.cypher
    else
        # Generate and execute Cypher commands based on files
        echo "Importing data using generated Cypher commands..."
        
        if [[ "${FILE_FORMAT}" == "csv" ]]; then
            # Process CSV files
            for CSV_FILE in "${IMPORT_DIR}"/*.csv; do
                if [[ -f "${CSV_FILE}" ]]; then
                    FILENAME=$(basename "${CSV_FILE}" .csv)
                    echo "Importing ${FILENAME} from CSV..."
                    
                    # Generate a simple LOAD CSV command
                    LOAD_COMMAND="LOAD CSV WITH HEADERS FROM 'file:///data/${FILENAME}.csv' AS row"
                    
                    if [[ "${FILENAME}" == *"node"* ]]; then
                        # Node import
                        LABEL=$(echo "${FILENAME}" | sed -E 's/.*_(.*)_node.*/\1/g')
                        CYPHER="${LOAD_COMMAND} CREATE (n:${LABEL}) SET n = row"
                    elif [[ "${FILENAME}" == *"rel"* ]]; then
                        # Relationship import
                        REL_TYPE=$(echo "${FILENAME}" | sed -E 's/.*_(.*)_rel.*/\1/g')
                        CYPHER="${LOAD_COMMAND} MATCH (source) WHERE source.id = row.source MATCH (target) WHERE target.id = row.target CREATE (source)-[r:${REL_TYPE}]->(target) SET r = row"
                    else
                        echo "Warning: Unknown file pattern for ${FILENAME}.csv, skipping..."
                        continue
                    fi
                    
                    # Execute the Cypher command
                    echo "${CYPHER}" > /tmp/import_command.cypher
                    docker cp /tmp/import_command.cypher ${CONTAINER_NAME}:/var/lib/neo4j/import/import_command.cypher
                    docker exec ${CONTAINER_NAME} cypher-shell -u neo4j -p password -f /var/lib/neo4j/import/import_command.cypher
                fi
            done
        elif [[ "${FILE_FORMAT}" == "json" ]]; then
            # Process JSON files
            for JSON_FILE in "${IMPORT_DIR}"/*.json; do
                if [[ -f "${JSON_FILE}" ]]; then
                    FILENAME=$(basename "${JSON_FILE}" .json)
                    echo "Importing ${FILENAME} from JSON..."
                    
                    # Generate APOC import command for JSON
                    if [[ "${FILENAME}" == *"node"* ]]; then
                        # Node import
                        LABEL=$(echo "${FILENAME}" | sed -E 's/.*_(.*)_node.*/\1/g')
                        CYPHER="CALL apoc.load.json('file:///data/${FILENAME}.json') YIELD value AS data UNWIND data AS row CREATE (n:${LABEL}) SET n = row"
                    elif [[ "${FILENAME}" == *"rel"* ]]; then
                        # Relationship import
                        REL_TYPE=$(echo "${FILENAME}" | sed -E 's/.*_(.*)_rel.*/\1/g')
                        CYPHER="CALL apoc.load.json('file:///data/${FILENAME}.json') YIELD value AS data UNWIND data AS row MATCH (source) WHERE source.id = row.source MATCH (target) WHERE target.id = row.target CREATE (source)-[r:${REL_TYPE}]->(target) SET r = row"
                    else
                        echo "Warning: Unknown file pattern for ${FILENAME}.json, skipping..."
                        continue
                    fi
                    
                    # Execute the Cypher command
                    echo "${CYPHER}" > /tmp/import_command.cypher
                    docker cp /tmp/import_command.cypher ${CONTAINER_NAME}:/var/lib/neo4j/import/import_command.cypher
                    docker exec ${CONTAINER_NAME} cypher-shell -u neo4j -p password -f /var/lib/neo4j/import/import_command.cypher
                fi
            done
        fi
    fi
else
    # Import using neo4j-admin import tool (for large datasets)
    echo "Importing data using neo4j-admin import..."
    
    # Stop Neo4j service
    docker exec ${CONTAINER_NAME} neo4j stop
    
    # Create import script based on available files
    # This is a simplified example - actual implementation would need to be customized
    if [[ "${FILE_FORMAT}" == "csv" ]]; then
        # Build import command for CSV files
        IMPORT_COMMAND="neo4j-admin database import full"
        
        # Add node files
        NODE_FILES=$(find "${IMPORT_DIR}" -name "*_node*.csv" | sort)
        for NODE_FILE in ${NODE_FILES}; do
            FILENAME=$(basename "${NODE_FILE}")
            LABEL=$(echo "${FILENAME}" | sed -E 's/.*_(.*)_node.*/\1/g')
            IMPORT_COMMAND="${IMPORT_COMMAND} --nodes=${LABEL}=/var/lib/neo4j/import/data/${FILENAME}"
        done
        
        # Add relationship files
        REL_FILES=$(find "${IMPORT_DIR}" -name "*_rel*.csv" | sort)
        for REL_FILE in ${REL_FILES}; do
            FILENAME=$(basename "${REL_FILE}")
            REL_TYPE=$(echo "${FILENAME}" | sed -E 's/.*_(.*)_rel.*/\1/g')
            IMPORT_COMMAND="${IMPORT_COMMAND} --relationships=${REL_TYPE}=/var/lib/neo4j/import/data/${FILENAME}"
        done
        
        # Add database name
        IMPORT_COMMAND="${IMPORT_COMMAND} --database=neo4j"
        
        # Execute import command
        docker exec ${CONTAINER_NAME} ${IMPORT_COMMAND}
    else
        echo "Error: neo4j-admin import currently only supports CSV format"
        exit 1
    fi
    
    # Start Neo4j service
    docker exec ${CONTAINER_NAME} neo4j start
    
    # Wait for Neo4j to start
    sleep 10
    
    # Verify Neo4j is running
    docker exec ${CONTAINER_NAME} neo4j status
fi

# Clean up import files in container
docker exec ${CONTAINER_NAME} rm -rf /var/lib/neo4j/import/data
docker exec ${CONTAINER_NAME} rm -f /var/lib/neo4j/import/import_command.cypher
docker exec ${CONTAINER_NAME} rm -f /var/lib/neo4j/import/import_script.cypher

echo "Import completed successfully."