#!/bin/bash

# Simplified script to set up Neo4j test database
# Uses the existing Neo4j container but with a dedicated test database

set -e

# Start Neo4j container if not already running
echo "Starting Neo4j container for testing..."
docker-compose up -d neo4j

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
MAX_ATTEMPTS=30
for i in $(seq 1 $MAX_ATTEMPTS); do
    if docker-compose exec -T neo4j cypher-shell -u neo4j -p password "RETURN 1 as num;" &> /dev/null; then
        echo "Neo4j is ready!"
        
        # Create dedicated test database
        echo "Creating test database..."
        docker-compose exec -T neo4j cypher-shell -u neo4j -p password "CREATE DATABASE codestory_test IF NOT EXISTS;"
        sleep 2  # Give it a moment to create the database
        
        # Verify test database exists and is accessible
        if docker-compose exec -T neo4j cypher-shell -u neo4j -p password -d codestory_test "RETURN 1 as num;" &> /dev/null; then
            echo "Test database 'codestory_test' is ready!"
            break
        else
            echo "Error: Could not connect to test database"
            exit 1
        fi
    fi
    
    if [ $i -eq $MAX_ATTEMPTS ]; then
        echo "Error: Neo4j failed to start within the timeout period"
        exit 1
    fi
    
    echo "Waiting for Neo4j to start... ($i/$MAX_ATTEMPTS)"
    sleep 2
done

# Clear test database to ensure clean state
echo "Clearing test database..."
docker-compose exec -T neo4j cypher-shell -u neo4j -p password -d codestory_test "MATCH (n) DETACH DELETE n;" || true

# Export environment variables for tests
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
export NEO4J_DATABASE="codestory_test"

echo "Neo4j test environment is ready. Environment variables have been set:"
echo "NEO4J_URI=$NEO4J_URI"
echo "NEO4J_USERNAME=$NEO4J_USERNAME"
echo "NEO4J_PASSWORD=$NEO4J_PASSWORD"
echo "NEO4J_DATABASE=$NEO4J_DATABASE"
echo ""
echo "Run tests with: 'pytest tests/integration/test_graphdb/'"