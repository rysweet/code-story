#!/bin/bash

# Script to stop the Neo4j test database container

echo "Stopping Neo4j test container..."
docker-compose -f docker-compose.test.yml down

echo "Neo4j test container stopped."