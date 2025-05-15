#!/bin/bash

# Script to stop all Code Story project components
# This script stops:
# 1. Neo4j database
# 2. Redis instance
# 3. Celery workers

set -e  # Exit on any error

# Function to print colored messages
print_header() {
  echo -e "\n\033[1;34m==== $1 ====\033[0m"
}

print_success() {
  echo -e "\033[1;32m✅ $1\033[0m"
}

print_info() {
  echo -e "\033[1;36m$1\033[0m"
}

print_error() {
  echo -e "\033[1;31m❌ $1\033[0m"
}

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
  if [[ -f "../pyproject.toml" ]]; then
    cd ..
  else
    print_error "Please run this script from the project root or scripts directory"
    exit 1
  fi
fi

print_header "Stopping Code Story Project"

# Stop Celery workers
print_info "Stopping Celery workers..."
CELERY_PID_FILE="$(pwd)/.celery.pid"

# First try to stop using the PID file (cleaner)
if [[ -f "$CELERY_PID_FILE" ]]; then
  CELERY_PID=$(cat "$CELERY_PID_FILE")
  if kill -0 $CELERY_PID 2>/dev/null; then
    print_info "Shutting down Celery worker with PID $CELERY_PID..."
    kill -TERM $CELERY_PID
    sleep 2
    # Check if process still exists
    if ! kill -0 $CELERY_PID 2>/dev/null; then
      print_success "Celery worker stopped successfully"
    else
      print_info "Celery worker didn't respond to TERM signal, using KILL..."
      kill -9 $CELERY_PID 2>/dev/null || true
    fi
    rm -f "$CELERY_PID_FILE"
  else
    print_info "PID file exists but process is not running"
    rm -f "$CELERY_PID_FILE"
  fi
# Fallback to process search
elif pgrep -f "celery.*codestory.ingestion_pipeline" > /dev/null; then
  print_info "Found Celery workers without PID file, stopping them..."
  pkill -f "celery.*codestory.ingestion_pipeline"
  print_success "Celery workers stopped"
else
  print_info "No Celery workers found running"
fi

# Stop Neo4j containers
print_info "Stopping Neo4j containers..."
if docker ps | grep -q "codestory-neo4j-test"; then
  # First try the docker-compose way
  docker-compose -f docker-compose.test.yml down -v
  print_success "Neo4j containers stopped via docker-compose"
else
  # Check if there's any stopped container with this name and remove it
  if docker ps -a | grep -q "codestory-neo4j-test"; then
    print_info "Found stopped Neo4j container, removing it..."
    docker rm -f codestory-neo4j-test
    print_success "Removed stopped Neo4j container"
  else
    print_info "No Neo4j containers found"
  fi
fi

# Clean up any volumes that might be left
if docker volume ls | grep -q "code-story_neo4j_test"; then
  print_info "Removing Neo4j volumes..."
  docker volume rm code-story_neo4j_test_data code-story_neo4j_test_logs 2>/dev/null || true
fi

# Stop Redis
print_info "Stopping Redis container..."
if docker ps | grep -q "codestory-redis"; then
  docker stop codestory-redis
  docker rm codestory-redis 2>/dev/null || true
  print_success "Redis container stopped and removed"
elif docker ps | grep -q "redis"; then
  print_info "Redis container exists but wasn't started by this script"
  print_info "Skipping Redis shutdown to avoid affecting other services"
else
  print_info "No Redis container found running"
fi

print_header "Environment Shutdown Complete"
print_success "All Code Story components have been stopped"