#!/bin/bash
# Start a Celery worker for the ingestion pipeline

# Change to the project root directory
cd "$(dirname "$0")/.."

# Check if Redis is running
echo "Checking if Redis is running..."
if ! nc -z localhost 6379; then
    echo "Redis is not running. Starting Redis with Docker..."
    docker run -d --name redis -p 6379:6379 redis:7-alpine
    
    # Wait for Redis to start
    echo "Waiting for Redis to start..."
    while ! nc -z localhost 6379; do
        sleep 1
    done
fi

echo "Setting up Python path..."
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Starting Celery worker..."
celery -A src.codestory.ingestion_pipeline.celery_app:app worker -l info -Q high,default,low