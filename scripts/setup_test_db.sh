#!/bin/bash

# Script to set up Neo4j test database for integration tests
# This script starts a Neo4j container for testing and sets up environment variables

set -e

# Start Neo4j container
echo "Starting Neo4j container for testing..."
docker-compose -f docker-compose.test.yml up -d neo4j

# Simple sleep to give Neo4j time to initialize
echo "Waiting for Neo4j to initialize (10 seconds)..."
sleep 10

# Try connecting in a loop
echo "Trying to connect to Neo4j..."
for i in {1..30}; do
    if docker-compose -f docker-compose.test.yml exec -T neo4j cypher-shell -u neo4j -p password "RETURN 1;" &> /dev/null; then
        echo "Neo4j is ready!"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo "Error: Neo4j failed to start within the timeout period"
        exit 1
    fi
    
    echo "Waiting for Neo4j to start... ($i/30)"
    sleep 2
done

# Clear test database to ensure clean state
echo "Clearing database..."
docker-compose -f docker-compose.test.yml exec -T neo4j cypher-shell -u neo4j -p password "MATCH (n) DETACH DELETE n;" || true

# Export environment variables for tests
export NEO4J_URI="bolt://localhost:7688"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
export NEO4J_DATABASE="codestory-test"

echo "Neo4j test environment is ready. Environment variables have been set:"
echo "NEO4J_URI=$NEO4J_URI"
echo "NEO4J_USERNAME=$NEO4J_USERNAME"
echo "NEO4J_PASSWORD=$NEO4J_PASSWORD"
echo "NEO4J_DATABASE=$NEO4J_DATABASE"
echo ""
echo "Run tests with: 'pytest tests/integration/test_graphdb/'"